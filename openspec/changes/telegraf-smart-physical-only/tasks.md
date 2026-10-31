# Tasks

## 1. Virtual-machine detection

- [x] 1.1 Add `hw_virtual` to `ansible/tasks/detect_hardware.yml`: `virtualization_role == 'guest'` and `virtualization_type` not in `docker`, `container`, `podman`, `lxc`; `false` for the container device; token `vm` in `MACHINE_HARDWARE`; header comment updated. Verify with `ansible-lint ansible/*.yml` and a dump run with `MACHINE_HARDWARE=vm`.
- [x] 1.2 Mirror `hw_virtual` in `tests/unit/package_sets.py` (default `False`) and add a virtual private server preset to `HOSTS`. Verify that `pytest tests/unit/test_package_presets.py -q` collects the new preset.

## 2. SMART fragment resolution

- [x] 2.1 In `ansible/tasks/resolve_monitoring.yml`, add `machine/smart` when the host is not `hw_virtual`, not `hw_pi`, not a container (by device and by virtualization type) and `influx_telegraf_config_base` is empty. Mirror it in `resolve_monitoring()` of `tests/unit/package_sets.py`. Verify with `pytest tests/unit/test_package_presets.py -q`: the mirror and `dump_monitoring.yml` agree for every preset, including virtual server, Pi, laptop and remote base.
- [x] 2.2 Update the expected fragment lists in `tests/unit/test_package_presets.py`: physical laptop and server get `machine/smart`, the virtual server and the Pi do not. Verify with the same test run.

## 3. Monitoring role

- [x] 3.1 Move `[[inputs.smart]]` from `files/machine_server.conf` into a new `files/machine_smart.conf` with `use_sudo = true`, `path_smartctl = "/usr/sbin/smartctl"` and `attributes = true`; no `[agent]` table. Verify with `test_fragments_have_no_agent_table` and a new test that only `machine_smart.conf` contains `inputs.smart`.
- [x] 3.2 In `roles/monitoring/tasks/main.yml`, when `machine/smart` is resolved and the host is Debian-family: install `smartmontools` and write `/etc/sudoers.d/telegraf-smartctl` (`0440`, `telegraf ALL=(root) NOPASSWD: /usr/sbin/smartctl`, `validate: visudo -cf %s`); otherwise remove that file. Make the sudoers path a role default, so the unit test can point it under `tmp_path`. Verify with a new `apply_role` test for both cases (rule written / removed) and `ansible-lint ansible/*.yml`.
- [x] 3.3 Remove local `machine_*.conf` fragments that are not resolved (local mode only), with a restart notification. Verify with an `apply_role` test that runs with `machine/smart`, then without it, and checks that `machine_smart.conf` is gone.
- [x] 3.4 Update `roles/monitoring/README.md` (inputs, SMART on physical non-Pi hosts, sudoers rule, no SMART with the remote base) and the hardware facts comment in `group_vars/all/packages.yml` if it lists them. Verify by reading the diff.

## 4. Validation

- [x] 4.1 Run `pytest tests/unit/test_monitoring_role.py tests/unit/test_package_presets.py tests/unit/test_telegraf.py -q`, then `pytest tests/unit -q`, because the hardware facts and the resolution are shared by packages and monitoring. Record the results.
- [x] 4.2 Run `ansible-lint ansible/*.yml` and `pre-commit run --files <changed paths>`, including the new `machine_smart.conf`. Record the results.
- [x] 4.3 Run the affected Docker integration tests (Readme "Tests") that apply the monitoring role, to check that test containers get no SMART fragment. Record the results.
- [ ] 4.4 After merging: run `machine update` on contabo and check `systemctl is-active telegraf` and that `machine_smart.conf` is absent; on homeserver check that `telegraf` is active and `journalctl -u telegraf` shows no SMART errors. Record the results.

## Validation record

- `pytest tests/unit/test_package_presets.py -q`: 33 passed (VM server, Pi, laptop and remote base resolve as specified; Python mirror equals `dump_monitoring.yml`).
- `pytest tests/unit/test_monitoring_role.py -q`: 15 passed (SMART fragment and sudoers rule written and removed; stale fragment removed).
- `pytest tests/unit -q`: 755 passed; full suite because the hardware facts and the fragment resolution are shared.
- `uvx ansible-lint ansible/*.yml`: 0 failures, 0 warnings. `pre-commit run --files <changed paths>`: clean after black and end-of-file fixes.
- `pytest tests/integration -m apt_gnome` (via `uv run --with-requirements tests/requirements.txt`): 1 passed; the container gets no `machine_smart.conf` and no sudoers rule.
- Detection on real hosts: this laptop `hw_virtual=False`; contabo reports `virtualization_role: guest`, `virtualization_type: kvm`.

## Workflow follow-up

- Archive the change with `/opsx:archive` once all tasks are done.
