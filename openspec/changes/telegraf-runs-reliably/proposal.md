# Proposal

## Why

With the feature `monitoring`, Telegraf should actually run on the host and ship metrics to Influx. Today it fails silently: Ubuntu has no `telegraf` package, setup does not fetch the Influx token, and nothing reports the problem. So monitoring is on, but nothing is measured.

## What Changes

- The `monitoring` role adds the InfluxData apt source with its signing key and installs `telegraf` from it. A failed install is no longer swallowed.
- `machine setup`, `machine apply` and the apply step of `machine update` read a dedicated Bitwarden item `influxdb-telegraf-write` before Ansible runs, when the host has `monitoring`. The values reach only the Ansible process (a private extra-vars file). They are not written to `~/.env`.
- The local fragments under `roles/monitoring/files/` stay the default config; with `INFLUX_TELEGRAF_CONFIG_BASE` set the remote configs replace them. The output (InfluxDB 2.x token or 1.x user/password) is generated from the item. When `INFLUX_TELEGRAF_CONFIG_BASE` is set, the remote configs are passed to the service in `/etc/default/telegraf` (`TELEGRAF_OPTS`, `INFLUX_TOKEN`, mode `0600`). This replaces the comment-only `00_remote_urls.conf`.
- Telegraf is enabled and started only when an output is configured. Without one it is stopped and disabled instead of crash-looping. A run without credentials keeps an existing output.
- `machine attention` gets a `monitoring` item when the host has `monitoring` and Telegraf is not installed, has no output, or is not active. Each case has its own text and resolution.
- Telegraf reports the system hostname; today local runs write `hostname = "localhost"`.
- The health check after apply stays a warning, but it names the reason (not installed / no output / not active).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `system-provisioning`: new requirements for Telegraf. Installed from the InfluxData source, local fragments as the default config, remote configs through the service environment instead of the local fragments, and started only with an output.
- `secret-tools`: new requirement for the Bitwarden item `influxdb-telegraf-write`, read before Ansible and kept out of the env files.
- `update-flow`: the attention entry point lists a monitoring item when Telegraf is not working on a host with `monitoring`.

Profiles affected: private hosts with `monitoring`. Work hosts and containers exclude `monitoring` and are unchanged.

## Impact

- `ansible/roles/monitoring/` (tasks, defaults, new key/source files, `/etc/default/telegraf` template), `ansible/group_vars/all/packages.yml` (influx vars).
- `machine_cli/tools.py` (`run_ansible` extra vars, health check), `machine_cli/commands.py` (setup/apply), `machine_cli/updates.py` (apply step), `machine_cli/attention.py`, `machine_cli/bw_client.py` (item read).
- Tests in `tests/unit/` (attention, influx extra vars) and `tests/integration/test_host_yaml_install.py` (role output).
- `Readme.md` (Monitoring section, Bitwarden items).
- External dependency: `repos.influxdata.com` apt repository.
