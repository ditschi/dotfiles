# Proposal

## Why

Every physical host with `monitoring` should report the health of its disks. Telegraf must not fail because of it: virtual machines have no real SMART data, and without `smartctl` Telegraf does not start at all.

Today the server fragment `machine/server` contains `[[inputs.smart]]`, but nothing installs `smartmontools` and the `telegraf` user may not read the disks. On contabo (a KVM server) the Ansible run fails at "Fail when telegraf does not keep running" with `smartctl not found`; on homeserver `telegraf` is inactive and `smartctl` is missing.

## What Changes

- Ansible detects whether the host is a virtual machine, as a new hardware fact next to laptop and Raspberry Pi.
- `[[inputs.smart]]` moves from `machine/server` into a new local fragment `machine/smart`.
- `machine/smart` is added on every physical host with `monitoring` that is not a Raspberry Pi, whatever its device (desktop or server). Virtual machines, containers and Raspberry Pis do not get it.
- On hosts with `machine/smart`, Ansible installs `smartmontools` and a sudoers rule that lets the `telegraf` user run only `smartctl` without a password; the fragment sets `use_sudo = true`.
- With `INFLUX_TELEGRAF_CONFIG_BASE` (remote configs), `machine/smart` is not requested; such hosts get no SMART input.
- A rootless Telegraf (for example installed with mise as a user service) is not part of this change: SMART needs root anyway, and the monitored hosts have root.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `hardware-detection`: adds the virtual-machine fact and the `machine/smart` fragment to the Telegraf fragment rule; `machine/server` no longer reads SMART.
- `system-provisioning`: adds installing `smartmontools` and the `smartctl` sudoers rule on hosts with `machine/smart`.

## Impact

Private hosts with `monitoring` (work hosts are not monitored). Physical desktops, laptops and servers gain the SMART input and the `smartmontools` package; virtual servers such as contabo lose it and Telegraf starts again. Raspberry Pis are unchanged.

Code: `ansible/tasks/detect_hardware.yml`, `ansible/tasks/resolve_monitoring.yml`, `ansible/roles/monitoring/` (new `files/machine_smart.conf`, tasks, README), the test mirror `tests/unit/package_sets.py` and the monitoring unit tests. No `machine` CLI change.

Made in the worktree `.worktrees/telegraf-smart-physical-only`, because `ansible/` is applied to the host by `machine apply` and `machine update`.
