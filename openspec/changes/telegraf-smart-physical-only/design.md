# Design

## Context

See proposal.md - Why. The Telegraf fragment names are resolved once in `ansible/tasks/resolve_monitoring.yml` from the hardware facts of `ansible/tasks/detect_hardware.yml`, the device and the features. The role `monitoring` copies `files/<name>.conf` for each name, or, with `INFLUX_TELEGRAF_CONFIG_BASE`, loads `<base>/<name>` instead. It then starts Telegraf and fails the run when the unit does not stay active. `tests/unit/package_sets.py` mirrors the resolution, and the unit tests compare that mirror with `ansible/dump_monitoring.yml`. Tests set the hardware through `MACHINE_HARDWARE` instead of detecting it.

Today `files/machine_server.conf` holds `[[inputs.smart]]`; nothing installs `smartmontools`, and the plugin runs `smartctl` as the unprivileged `telegraf` user, which cannot read the disks.

## Goals / Non-Goals

**Goals:**
- Telegraf starts on every monitored host again, virtual or physical.
- Physical hosts (except Raspberry Pis) report SMART data with the least privilege that works.

**Non-Goals:**
- A rootless Telegraf (for example installed with mise and run as a user service) for hosts without root.
- SMART through the remote configs of `INFLUX_TELEGRAF_CONFIG_BASE`.
- Vendor-specific NVMe attributes that need `nvme-cli`.

## Decisions

**System Telegraf through Ansible, not a rootless Telegraf.** The owner chose to keep the Ansible-managed system service. Reading SMART needs raw device access (`CAP_SYS_RAWIO`, for NVMe `CAP_SYS_ADMIN`), so a rootless Telegraf could never report SMART, and the monitored hosts have root. A rootless Telegraf would add linger, its own update path and a second set of configs, for metrics the system service already collects. It may come back later as a separate feature for hosts without root.

**A separate fragment `machine/smart`.** The owner chose a separate fragment over a templated server fragment. SMART then follows the hardware instead of the device, and the resolved names show whether a host reads SMART. With the remote base, `machine/smart` is not resolved, so the remote side needs no new config; the owner accepted that such hosts report no SMART data.

**SMART on all physical hosts except Raspberry Pis.** The owner extended SMART from servers to every physical host with `monitoring`, desktops and laptops included. Raspberry Pis are left out: their SD cards and most USB adapters offer no SMART data, and a Pi Zero should not carry the extra package.

**Virtual-machine detection from the Ansible facts.** `hw_virtual` is true when `ansible_facts.virtualization_role` is `guest` and `virtualization_type` is not a container type (`docker`, `container`, `podman`, `lxc`, the list `sshd_home` already uses). The facts are gathered anyway, so no extra command such as `systemd-detect-virt` runs. Containers get `hw_virtual: false` like the other hardware facts, and the SMART fragment is also left out when the virtualization type is a container type, so a test container never gets SMART. `MACHINE_HARDWARE` gains the token `vm` for tests.

**`use_sudo` with a narrow sudoers rule instead of capabilities.** `/etc/sudoers.d/telegraf-smartctl` (mode `0440`) holds `telegraf ALL=(root) NOPASSWD: /usr/sbin/smartctl`, written with `validate: visudo -cf %s`. The fragment sets `use_sudo = true` and `path_smartctl = "/usr/sbin/smartctl"`. This is the way the Telegraf SMART plugin documents. Giving the whole `telegraf.service` `CAP_SYS_RAWIO`/`CAP_SYS_ADMIN` through a drop-in was rejected: it would give every input those rights, not only `smartctl`.

**Stale fragments are removed.** Today the role only copies the resolved fragments; a host that stops resolving `machine/smart` (a VM, or one switched to the remote base) would keep loading `machine_smart.conf`. The role removes local `machine_*.conf` files that are not resolved, and the sudoers rule when `machine/smart` is not resolved. `smartmontools` stays installed: removing a package other tools may use is not worth it.

## Risks / Trade-offs

- [`smartctl` as root can change device settings or start self-tests, not only read] → Only `telegraf` gets the rule, only for `smartctl`; a compromised `telegraf` user is already able to read the Docker socket on Docker hosts. Restricting the arguments in sudoers was rejected as brittle across plugin versions.
- [Disks behind USB adapters without SMART pass-through make `smartctl` fail] → The plugin logs a gather error and Telegraf keeps running; the start check only fails on a stopped unit.
- [A misdetected VM gets SMART again and Telegraf fails as before] → The start check reports it; `MACHINE_HARDWARE` and the `vm` token make the case testable.
- [Removing `monitoring` from a host does not run the role, so its sudoers rule stays] → Like the `telegraf` package itself; acceptable for a rule that only lets `telegraf` run `smartctl`.

## Migration Plan

`machine update` (or `machine apply`) on each monitored host applies the change. On contabo, `machine_server.conf` loses `[[inputs.smart]]` and Telegraf starts. On homeserver and the laptop, `smartmontools`, the sudoers rule and `machine_smart.conf` are added. Rollback: revert the commit and run `machine apply`.
