# Tasks

## 1. Influx credentials from Bitwarden

- [x] 1.1 Add a reader for the item `influxdb-telegraf-write` to `machine_cli/bw_client.py` that returns its values as a dict (custom fields first; login password → `INFLUX_TOKEN`, first URI → `INFLUX_URL` when those fields are absent), logs a missing or locked item without prompting outside a terminal, and is cached per command. Verify with unit tests for a field-only item, a login item, field-over-login precedence, missing and locked.
- [x] 1.2 In `ToolsMixin.run_ansible` (`machine_cli/tools.py`), when the target host config lists `monitoring`, write the values as `influx_*` Ansible variables to a private temp file (`0600`, removed at exit, same helper as the become-password file) and pass it as an extra `--extra-vars @file`. Verify with unit tests: the command contains the file for a monitoring host and not otherwise, the file is gone after the run, and no `~/.env*` file is touched.
- [x] 1.3 Keep the `lookup('env', …)` defaults in `ansible/group_vars/all/packages.yml` as a fallback and update their comment to name the Bitwarden item. Verify with `ansible-lint ansible/*.yml`.
- [x] 1.4 Document the item `influxdb-telegraf-write` (fields, which are required) next to `ansible-vault` in `Readme.md`. Verify that the Readme names every field the role reads.

## 2. Monitoring role

- [x] 2.1 Add the InfluxData signing key under `ansible/roles/monitoring/files/` and a deb822 `.sources` template with `Signed-By` (pattern of `roles/cosmic_desktop`), and install `telegraf` without `failed_when: false`. Verify in the Docker APT test that `telegraf` is installed on Ubuntu.
- [x] 2.2 Replace `00_remote_urls.conf` with `/etc/default/telegraf` (`0600`, root) holding `TELEGRAF_OPTS` with one `--config <base>/<name>` per resolved name and `INFLUX_TOKEN`. With a remote base, remove the local fragment files; without one, remove or empty `TELEGRAF_OPTS`. Verify with role tests in `tests/unit/test_monitoring_role.py` for both cases.
- [x] 2.3 Keep the output templates, keep an existing `99_output_*.conf` when no credentials are given, and remove the stale 1.x/2.x counterpart when the other is written. Verify with a role test in `tests/unit/test_monitoring_role.py` that a run without credentials leaves an existing output unchanged.
- [x] 2.4 Decide "has output" from `99_output_*.conf` or a non-empty `TELEGRAF_OPTS`. With an output, enable and start `telegraf` (no `failed_when: false`) and restart it through a handler on config changes. Without one, stop and disable it and print a message naming `influxdb-telegraf-write`. Verify with role tests for both states and the Docker APT tests (installed, no output).
- [x] 2.5 Update `ansible/roles/monitoring/README.md` and the Monitoring section of `Readme.md` (source, config default, remote base, start rule). Verify with `pre-commit run --all-files`.
- [x] 2.6 Drop the `hostname` setting from `telegraf.conf`, so Telegraf reports the system hostname instead of the inventory name `localhost` of local runs. Verify with a role test in `tests/unit/test_monitoring_role.py`.
- [x] 2.7 Add `telegraf` to the group `docker` with the fragment `machine/docker`, flush handlers before the start and fail the run when the unit does not stay `active`. Verify with `ansible-lint` and `machine apply` on the laptop (task 4.2).

## 3. Telegraf state in the CLI

- [x] 3.1 Add a Telegraf check that returns `None` or one reason (not installed / no output / not active) without root, from the binary, the output files or an enabled unit (`/etc/default/telegraf` is root-only), and `systemctl is-active`. Verify with unit tests for each state and for a host without `monitoring`.
- [x] 3.2 Use the check in `health_check_after_apply` as a warning that names the reason and never sets `ok = False`. Verify with a unit test that an inactive Telegraf keeps the apply.
- [x] 3.3 Add the `monitoring` item to `attention_items()` in `machine_cli/attention.py`: not installed → offer `machine apply`; no output → name `influxdb-telegraf-write` and offer `machine apply`; not active → show `journalctl -u telegraf -n 20 --no-pager` (best effort) and offer `sudo systemctl restart telegraf`. Verify with unit tests for the listing, the non-interactive run and each resolution.
- [x] 3.4 Mention the monitoring item in the `machine attention` part of `Readme.md`. Verify that the Readme list matches the spec `update-flow` "Attention entry point".

## 4. Integration checks

- [x] 4.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `ansible-lint ansible/*.yml`, and verify all pass.
- [x] 4.2 On the owner's laptop, after creating `influxdb-telegraf-write`, run `machine apply`. Verify that `systemctl is-active telegraf` prints `active`, metrics arrive in the bucket, and `machine attention` lists no monitoring item. Before creating the item, verify that `machine attention` lists the "no output" item.

## Workflow follow-up

- Remove `INFLUX_*` from the env items in Bitwarden if they exist there.
- Archive the change after review (`/opsx:archive`).
