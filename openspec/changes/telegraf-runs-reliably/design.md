# Design

## Context

See proposal.md for the motivation. What is there today:

- `roles/monitoring` installs `telegraf` with `failed_when: false`. Ubuntu 26.04 has no such package and no InfluxData source is configured, so nothing is installed. `service: telegraf started` also uses `failed_when: false` and fails silently because there is no unit.
- The Influx values come from `lookup('env', …)` in `group_vars/all/packages.yml`. `machine setup` runs Ansible before `cmd_env_pull`, and the `machine` process sees `INFLUX_*` only if the calling shell had loaded `~/.env*`. On the owner's laptop no `INFLUX_*` value is set anywhere.
- Without an output, Telegraf exits with "no outputs found". With `Restart=on-failure` in the upstream unit it would loop.
- With `INFLUX_TELEGRAF_CONFIG_BASE` set, `00_remote_urls.conf` holds only a comment. The service never loads the remote configs.
- The upstream `telegraf.service` reads `EnvironmentFile=-/etc/default/telegraf` and appends `$TELEGRAF_OPTS` to its command line.
- All Ansible runs (setup, apply, the revert re-run, the update apply step, remote `--limit`) go through `ToolsMixin.run_ansible`, which already passes the host config as `--extra-vars @file`.
- `health_check_after_apply` must not fail on Telegraf. Earlier stricter checks rolled back successful applies (see `openspec/investigations/env-and-update.md`).

## Goals / Non-Goals

**Goals:**
- A fresh `machine setup` on a private host with `monitoring` ends with Telegraf active and shipping metrics, without any manual step besides an unlocked Bitwarden.
- Every way Telegraf can be broken on such a host shows up in `machine attention`.

**Non-Goals:**
- No prompt segment or shell-start message for Telegraf. The item shows only in `machine` / `machine attention`, and the background job records nothing for it.
- No per-host Influx credentials. One item serves all hosts.
- No change to which fragments a host gets (`tasks/resolve_monitoring.yml` stays the single source).
- No Telegraf for hosts that are not Debian-family.

## Decisions

### A dedicated Bitwarden item, passed only to Ansible
The credentials live in their own item `influxdb-telegraf-write`, read like `ansible-vault`. `run_ansible` reads it when the target host config lists `monitoring` and writes the values as Ansible variables (`influx_url`, `influx_token`, …) to a private temp file (`0600`, removed at exit, same helper as the become-password file). It passes that file as a second `--extra-vars @file`. Extra vars override the `lookup('env')` defaults, which stay as a fallback for runs with `INFLUX_*` in the environment. The item is read once per `machine` command and cached, so the revert re-run does not ask Bitwarden again. Missing or locked: log and continue (spec `secret-tools`). Values come from custom fields named like the variables; for a login item, the password and first URI fill `INFLUX_TOKEN` and `INFLUX_URL` when those fields are absent. The owner created the item as `influxdb-telegraf-write`, so the code uses that name. It is a login item: the password holds the token, and the fields `INFLUX_URL`, `INFLUX_ORG` and `INFLUX_BUCKET` hold the rest.

Reason: the token is a credential of a system service. It does not belong in every shell, and Ansible needs it in the same run, before `cmd_env_pull` would run.

Rejected: keeping `INFLUX_*` in the env items (`env/groups/<group>`) and moving the env pull before Ansible. That puts the token into every shell and still depends on the `machine` process environment.

### Local fragments are the default config, remote configs replace them when set
The fragments under `roles/monitoring/files/` are versioned in the repo and stay the source of inputs. The output file is generated from the item. When `INFLUX_TELEGRAF_CONFIG_BASE` is set, the role writes `/etc/default/telegraf` (`0600`, root) with `TELEGRAF_OPTS="--config <base>/<name> …"` and `INFLUX_TOKEN=…`, which the upstream unit already reads. The local fragment files are then removed, as they are not deployed today, so inputs are not doubled. `00_remote_urls.conf` is removed. Without a remote base, `/etc/default/telegraf` is absent or has empty `TELEGRAF_OPTS`.

Rejected: remote configs from InfluxDB as the default. Every start would depend on the Influx server and its config store, and the inputs would not be versioned with the repo.

### InfluxData apt source like the COSMIC PPA
The role ships the InfluxData signing key under `files/` and a deb822 `.sources` template with `Signed-By`, following `roles/cosmic_desktop`. Then it runs `apt: telegraf` without `failed_when: false`. The source uses the `stable` suite of `repos.influxdata.com/debian`, which serves Debian and Ubuntu on amd64 and arm64/armhf (Raspberry Pi).

### "Has an output" is decided from the files on disk
The role decides from whether `/etc/telegraf/telegraf.d/99_output_*.conf` exists, or `TELEGRAF_OPTS` names remote configs. It does not decide from whether credentials were present in this run. That keeps a working host working when Bitwarden is locked during an apply. The CLI runs without root and cannot read `/etc/default/telegraf` (`0600`, it holds the token). So it counts an output file (the directory is `0755`) or an enabled `telegraf` unit as an output: the role enables the unit only with an output and disables it without one.

### Output files readable by the service group
The output files hold the token. They belong to `root:telegraf` with mode `0640`, because the service runs as the user `telegraf`; mode `0600` (root only) made Telegraf fail with "permission denied" on the first real apply. `/etc/default/telegraf` stays `0600`, because systemd reads it as root.

### Start only with an output
With an output: `service: telegraf enabled started` without `failed_when: false`, plus a handler that restarts on config changes. The handlers are flushed before the start, and the role then checks for a few seconds that the unit stays `active`, because Telegraf exits right after a successful start when an input fails.

With the fragment `machine/docker`, the user `telegraf` joins the group `docker` (when it exists), so `inputs.docker` can read `/var/run/docker.sock`. The docker group is root-equivalent; that is the price of the Docker metrics the fragment exists for. Without one: `stopped`, `enabled: false`, and a debug line naming `influxdb-telegraf-write`.

### Attention item from live checks
`attention_items()` adds at most one `monitoring` item when `monitoring` is in `saved_features()` and `systemctl` exists. It is checked in this order:

1. No `telegraf` binary: offer `machine apply`.
2. No output: name `influxdb-telegraf-write` and offer `machine apply`.
3. `systemctl is-active telegraf` not `active`/`activating`: print `journalctl -u telegraf -n 20 --no-pager` (best effort, may need the adm/systemd-journal group), then offer `sudo systemctl restart telegraf`.

The health check after apply uses the same check function and logs its reason as a warning.

## Risks / Trade-offs

- [InfluxData key rotation or repository outage breaks `machine apply` on monitoring hosts] → The install fails loudly and names Telegraf. Updating the key file is a one-file change.
- [Bitwarden locked during an unattended or remote apply] → Credentials are optional per run, and the existing output is kept.
- [Temp file with the token on disk during the run] → `0600` in the user's temp dir, removed by `atexit`, same as the become password today.
- [Journal not readable without group membership] → The item still names the state and offers the restart. The journal lines are best effort.

## Migration Plan

1. The Bitwarden item `influxdb-telegraf-write` exists (login password = token, fields `INFLUX_URL`, `INFLUX_ORG`, `INFLUX_BUCKET`).
2. Run `machine apply` on each monitoring host. Telegraf gets installed, the output is written and the service starts.
3. If `INFLUX_*` is in an env item today, remove it there once the dedicated item exists.

Rollback: revert the commit. An installed `telegraf` and its source stay on the host (same as "Deselecting COSMIC removes nothing").
