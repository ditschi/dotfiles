# Proposal

## Why

The feature `thinkpad-tuning` bundles settings for one machine, the ThinkPad L13 Yoga Gen 2, but most of them suit every laptop, and one does not depend on the hardware at all. The owner has a second ThinkPad without touch screen or stylus that will get the dotfiles, and other laptops (also non-ThinkPads) need different tuning. The laptop now suspends when the lid is closed; the owner wants closing the lid to do nothing, on battery and on the charger, on all laptops. Settings that suit any laptop or any host shall therefore be separate features in the feature table, and the tuning for one model shall be applied automatically on that model and never offered on other machines.

## What Changes

- **BREAKING** The feature `thinkpad-tuning` and the role `thinkpad_tuning` are removed. Their parts become separate features or a model role; host configs that list `thinkpad-tuning` are migrated in this change.
- New feature `lid-switch`: closing the lid does nothing, on battery, on the charger and when docked (systemd-logind drop-in).
- New feature `power-profile-switch`: the power profile follows the power source (`performance` on the charger, `balanced` on battery), as before; a profile the host does not offer is skipped instead of failing.
- New feature `battery-charge-limit`: battery charge thresholds (start below 75 %, stop at 80 %) through the kernel's generic battery interface, with the command to charge to full before a trip and back; a battery that only offers a stop threshold is supported.
- The three laptop features are preselected on desktops for both contexts and excluded on servers and in containers. Ansible applies them only on hosts it detects as laptops, so a desktop PC or the work VM can keep them selected without effect.
- New feature `zram-swap`: compressed swap in RAM, preferred over the swap file on disk, as before. Preselected on desktops and servers for both contexts, excluded in containers; Ansible does not apply it on a detected Raspberry Pi.
- New role for the ThinkPad L13 Yoga Gen 2 (S3 suspend and the on-screen keyboard in tablet mode). It is not a feature: Ansible applies it when the hardware reports this model, never in a container, and other machines never see it in the feature menu.
- Host configs: the L13 Yoga and the work laptop `LR-C-0042H` get the three laptop features and `zram-swap`; the work VM `ABTVL421` and `homeserver` get `zram-swap`; `thinkpad-tuning` is removed everywhere, including the CI host config that mirrors the L13 Yoga.

## Capabilities

### New Capabilities
- `hardware-tuning`: what the lid, power profile, charge limit and zram features do, on which hardware Ansible applies them, and how model-specific tuning is selected by the hardware itself.

### Modified Capabilities
- `feature-selection`: table rows for `lid-switch`, `power-profile-switch`, `battery-charge-limit` and `zram-swap`; `thinkpad-tuning` removed.
- `system-provisioning`: the list of local Ansible roles changes (`thinkpad_tuning` is replaced by the new roles).

Affected hosts: laptops (L13 Yoga, `LR-C-0042H`, later the T470) get the laptop features; every non-container host can get `zram-swap`; Raspberry Pis are unchanged.

## Impact

- Ansible: `ansible/roles/thinkpad_tuning` is split into new roles `lid_switch`, `power_profile_switch`, `battery_charge_limit`, `zram_swap` and `thinkpad_l13_yoga_gen2`; `ansible/workstation.yml`; `ansible/group_vars/all/features.yml` and `packages.yml`; `ansible/tasks/detect_hardware.yml` (model fact).
- Host configs under `machine/hosts/` and `tests/hosts/ci-home-laptop.yml`.
- On the L13 Yoga, files installed by the old role (for example `/usr/local/bin/thinkpad-charge`, `/etc/default/thinkpad-tuning`, the `thinkpad-*` units and udev rule, `/etc/default/grub.d/thinkpad-tuning.cfg`) are replaced by the new ones.
- Tests: `tests/integration/test_host_yaml_install.py`, unit tests for the feature table and the scripts. Docs: Readme, `ansible/README.md`, `docs/thinkpad-l13-yoga-gen2.md`.
