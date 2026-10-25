# Tasks

## 1. Lid switch

- [ ] 1.1 Add role `ansible/roles/lid_switch` (logind drop-in `/etc/systemd/logind.conf.d/50-lid-switch.conf` with the three `HandleLidSwitch*=ignore` lines, handler that reloads logind with `SIGHUP` when `machine_manage_services`) and its play in `ansible/workstation.yml` gated by `'lid-switch' in machine_features` and `hw_laptop`. Verify `ansible-lint ansible/*.yml` passes.
- [ ] 1.2 Add the `lid-switch` row to `features.yml` (desktop default, server and container excluded). Verify `pytest tests/unit -q` passes, including a feature-table test for the new rows.

## 2. Power profile switch

- [ ] 2.1 Add role `ansible/roles/power_profile_switch` from the power profile parts of `thinkpad_tuning`: script `power-profile-switch` (skip with a log line and exit 0 when `powerprofilesctl list` lacks the profile), unit `power-profile-switch.service`, udev rule, settings `/etc/default/power-profile-switch`, variables `power_profile_switch_ac` / `_battery`; remove the old `thinkpad-power-profile` script, unit and udev rule (disable the unit first). Gate the play on the feature and `hw_laptop`. Verify `ansible-lint ansible/*.yml` passes.
- [ ] 2.2 Add a unit test that runs the script against a fake `/sys/class/power_supply` and a stub `powerprofilesctl`: charger online, on battery, profile not offered. Verify the test passes.
- [ ] 2.3 Move `power-profiles-daemon` in `packages_by_feature` to `power-profile-switch` and add the table row. Verify `pytest tests/unit -q` passes.

## 3. Battery charge limit

- [ ] 3.1 Add role `ansible/roles/battery_charge_limit` from the charge parts of `thinkpad_tuning`: command `/usr/local/bin/battery-charge` (`status|normal|full`; start threshold only when present), unit `battery-charge-limit.service` without the `thinkpad_acpi` condition, settings `/etc/default/battery-charge-limit`, variables `battery_charge_limit_start` / `_stop`; remove `/usr/local/bin/thinkpad-charge` and `thinkpad-charge-thresholds.service` (disable first). Gate the play on the feature and `hw_laptop`. Verify `ansible-lint ansible/*.yml` passes.
- [ ] 3.2 Add a unit test that runs `battery-charge` against fake batteries: start and stop threshold, stop only, two batteries, none. Verify the test passes.
- [ ] 3.3 Add the table row. Verify `pytest tests/unit -q` passes.

## 4. zram swap

- [ ] 4.1 Add role `ansible/roles/zram_swap` with the zram generator config and sysctl file of `thinkpad_tuning` (same paths), variable `zram_swap_size`; gate the play on the feature and `not hw_pi`; move `systemd-zram-generator` in `packages_by_feature` to `zram-swap` (packages only when not on a Pi). Verify `ansible-lint ansible/*.yml` passes.
- [ ] 4.2 Add the table row (desktop and server default, container excluded). Verify `pytest tests/unit -q` passes, including the package resolver for a Pi with `zram-swap`.

## 5. L13 Yoga Gen 2 model role

- [ ] 5.1 Rename the rest of `thinkpad_tuning` (S3 suspend, warning, tablet on-screen keyboard) to role `ansible/roles/thinkpad_l13_yoga_gen2` with variable `thinkpad_l13_yoga_gen2_mem_sleep`; the GRUB drop-in becomes `/etc/default/grub.d/thinkpad-l13-yoga-gen2.cfg` and the old `thinkpad-tuning.cfg` is removed (one `update-grub`). Add `hw_model_l13_yoga_gen2` to `detect_hardware.yml` (DMI vendor and version, not in containers; `MACHINE_HARDWARE=l13-yoga-gen2` in tests) and gate the play on it. Verify `ansible-lint ansible/*.yml` passes and the fact is true on this laptop.
- [ ] 5.2 Remove `thinkpad-tuning` from the feature table and `packages_by_feature`, move `vainfo` to `desktop`, delete `ansible/roles/thinkpad_tuning`. Verify `git grep -n thinkpad.tuning` only finds archived OpenSpec files and `pytest tests/unit -q` passes.

## 6. Host configs, tests and docs

- [ ] 6.1 Migrate host configs: `ditschi-ThinkPad-L13-Yoga-Gen-2.yml` and `LR-C-0042H.yml` get `lid-switch`, `power-profile-switch`, `battery-charge-limit`, `zram-swap` (L13 drops `thinkpad-tuning`); `ABTVL421.yml` and `homeserver.yml` get `zram-swap`; `tests/hosts/ci-home-laptop.yml` mirrors the L13 file and its test sets `MACHINE_HARDWARE=laptop,l13-yoga-gen2`. Verify `test_repo_host_yamls_are_valid` passes.
- [ ] 6.2 Update `tests/integration/test_host_yaml_install.py` (`battery-charge` instead of `thinkpad-charge`, logind drop-in exists, tablet unit from the model role). Verify `pytest tests/integration -m docker -n auto` passes.
- [ ] 6.3 Update the Readme, `ansible/README.md` and `docs/thinkpad-l13-yoga-gen2.md` (which features and the model role set what; `battery-charge`; lid). Verify the documented commands match the scripts.

## 7. Checks

- [ ] 7.1 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and `openspec validate split-laptop-tuning --strict`. Verify all pass.
- [ ] 7.2 Run `machine testenv -- 'cd ~/dotfiles && machine apply'`, then `machine apply` on the L13 Yoga. Verify: closing the lid does nothing on battery and on the charger; `battery-charge` shows 75–80 %; `powerprofilesctl get` follows plug/unplug; `swapon --show` lists zram; `cat /sys/power/mem_sleep` shows `[deep]`; the old `thinkpad-*` files and units are gone.

## Workflow follow-up

- Archive the change after review; the archive adds the `hardware-tuning` spec and updates `feature-selection` and `system-provisioning`.
