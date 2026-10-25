# Design

## Context

Builds on `profile-axes` (archived 2026-10-25): hosts have a context and a device, the feature table `ansible/group_vars/all/features.yml` decides defaults and exclusions, Ansible applies only `machine_features`, and `ansible/tasks/detect_hardware.yml` sets `hw_laptop`, `hw_pi` and `hw_pi_zero` (or takes them from `MACHINE_HARDWARE` in tests).

The role `ansible/roles/thinkpad_tuning`, enabled by the feature `thinkpad-tuning` (table: optional on desktops), sets five things on the ThinkPad L13 Yoga Gen 2: battery charge thresholds, power profile per power source, S3 suspend, zram swap and the on-screen keyboard in tablet mode. One settings file `/etc/default/thinkpad-tuning` feeds the charge and power profile scripts. The L13 Yoga host config and `tests/hosts/ci-home-laptop.yml` list the feature.

Observed facts that shape the approach:
- The charge script already uses the kernel's generic battery interface (`/sys/class/power_supply/BAT*/charge_control_{start,end}_threshold`); only its unit has `ConditionPathIsDirectory=/sys/devices/platform/thinkpad_acpi`. It writes the start threshold unconditionally, which fails with `set -e` on batteries that only offer a stop threshold.
- The power profile script calls `powerprofilesctl set` without checking that the profile exists (placeholder driver).
- The lid action is decided by systemd-logind (`HandleLidSwitch=suspend` by default). `/etc/systemd/logind.conf` on the L13 Yoga is the unmodified package file and no `logind.conf.d/` exists; the journal shows `Lid closed. → Suspending...`.
- Ansible facts expose the DMI data: `ansible_system_vendor` (`LENOVO`), `ansible_product_version` (`ThinkPad L13 Yoga Gen 2`). In a Docker container the facts show the host's hardware.

See proposal.md for the motivation and the specs for the required behaviour.

## Goals / Non-Goals

**Goals:**
- One role per concern, applied through the feature table like every other feature, and only on hardware where it makes sense.
- Model tuning that cannot be selected by mistake on other hardware.
- The L13 Yoga keeps its current behaviour after migration, plus the lid setting.

**Non-Goals:**
- Tuning for the second ThinkPad (T470) beyond the generic features; a model role for it can follow when needed.
- Locking the screen or other actions on lid close.

## Decisions

- **Laptop settings are features in the table (owner decision).** `lid-switch`, `power-profile-switch` and `battery-charge-limit` are preselected on desktops and excluded on servers and in containers, and their roles run only when `hw_laptop` is true. They stay visible and can be deselected per host like any other feature. Applying them automatically on detected laptops without a feature, with an opt-out variable, was considered and not taken because it would add a second mechanism next to the table.
- **No generic ThinkPad role (owner decision).** Once lid, power profile, charge limit and zram are separate, nothing ThinkPad-specific remains: the charge thresholds use the generic kernel interface.
- **Charge limit separate from the power profile (owner decision).** The power profile trades speed against runtime now, the charge limit protects the battery over years.
- **zram as a feature, not on Raspberry Pis (owner decision).** Preselected on desktops and servers, excluded in containers; the role is skipped when `hw_pi` is true.
- **Lid via a logind drop-in.** The role `lid_switch` writes `/etc/systemd/logind.conf.d/50-lid-switch.conf` with `HandleLidSwitch=ignore`, `HandleLidSwitchExternalPower=ignore` and `HandleLidSwitchDocked=ignore`. A drop-in survives package updates. The handler reloads logind with `SIGHUP` instead of a restart, which can end the graphical session. GNOME's `lid-close-*-action` keys were not used: logind makes the decision.
- **Power profile script.** Installed as `power-profile-switch` with settings in `/etc/default/power-profile-switch`; before setting it checks `powerprofilesctl list` and otherwise logs and exits 0.
- **Charge limit command `battery-charge`** (`status`, `normal`, `full`) with settings in `/etc/default/battery-charge-limit`; it writes the start threshold only when the battery offers one; the unit has no ThinkPad condition.
- **Model role selected by DMI facts (owner decision).** `thinkpad_l13_yoga_gen2` runs when `ansible_system_vendor == 'LENOVO'`, `ansible_product_version == 'ThinkPad L13 Yoga Gen 2'` and the device is not `container` (a container sees the host's DMI data). The match is exact, so other generations do not get Gen 2 settings. A feature shown only on matching hardware was considered and not taken; the owner wants no choice for model tuning. `MACHINE_HARDWARE` gets a value `l13-yoga-gen2` so that the CI host config can stand for this model.
- **Old files are removed by the new roles.** Each new role deletes the paths it replaces (`/usr/local/bin/thinkpad-charge`, `/usr/local/lib/machine/thinkpad-power-profile`, `/etc/default/thinkpad-tuning`, `thinkpad-charge-thresholds.service`, `thinkpad-power-profile.service`, `85-thinkpad-power-profile.rules`, `/etc/default/grub.d/thinkpad-tuning.cfg`), disabling the old units first. The zram files keep their paths. The cleanup tasks can be dropped once no host has the old files.
- **Relevance filter.** Role conditions on hardware facts cannot be evaluated by `machine update`'s relevance filter, so changes to these roles count as relevant; this errs towards an extra Ansible run.

## Risks / Trade-offs

- [Closing the lid in a bag with the laptop running drains the battery and heats it] → wanted by the owner; suspend stays available through the menu and the power button.
- [`ansible_product_version` differs between BIOS versions or is empty] → the model role is then not applied; the L13 Yoga's value is verified on the machine.
- [The old role's files stay if a host leaves the feature list before the cleanup runs] → only the L13 Yoga had the old role, and it gets the new features in the same change.
- [`performance` on the charger raises power use] → unchanged behaviour; the profile is configurable per host.

## Migration Plan

1. Implement the roles, the table rows and the model detection; migrate the host configs in the same commit.
2. Run `machine apply` on the L13 Yoga: new files are installed, old files removed, logind reloaded. Check lid, `battery-charge`, `powerprofilesctl get`, `swapon --show`, `cat /sys/power/mem_sleep`.
3. Other hosts pick up the change with their next `machine update`.
4. Rollback: revert the commit and run `machine apply`; the old role reinstalls its files. The logind drop-in would stay and must be deleted by hand.

## Assumptions

- The package `vainfo` (listed under `thinkpad-tuning` as a VA-API check tool) moves to the feature `desktop`, because it is not tied to one model.
- The settings variables keep their values and get role prefixes (for example `battery_charge_limit_start`, `power_profile_switch_ac`, `zram_swap_size`, `thinkpad_l13_yoga_gen2_mem_sleep`).
