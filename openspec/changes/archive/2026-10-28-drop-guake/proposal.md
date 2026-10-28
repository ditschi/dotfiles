# Proposal

## Why

The owner uses the Ddterm GNOME Shell extension as the drop-down terminal and no longer uses Guake. The dotfiles still install Guake with the feature `gnome` and set its font, so `machine apply` puts Guake back after the owner removed it (seen on 2026-10-28), and the Nerd Font goes to a terminal that is not used while Ddterm keeps the system font.

## What Changes

- The feature `gnome` no longer installs the apt package `guake`.
- An existing Guake installation is not removed. Deselecting or dropping a package removes nothing, as for the other package features.
- `machine` no longer sets the Guake font. No other Guake setup remains in the repository.
- With the feature `fonts`, `machine` sets the Ddterm terminal font to the Nerd Font (`FiraCode Nerd Font Mono`), keeping the current size, as it did for Guake.
- The help text of `gnome` and the Readme no longer name Guake.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-tools`: the requirement "GNOME drop-down terminal extension" no longer keeps Guake installed; Guake is neither installed nor configured. A new requirement sets the Nerd Font in Ddterm.

Affected hosts: desktops with the feature `gnome` (private and work, the default on desktops). Servers and containers are not affected.

## Impact

- Ansible: `guake` removed from `packages_by_feature.gnome` in `ansible/group_vars/all/packages.yml`; help text of `gnome` in `ansible/group_vars/all/features.yml`.
- `machine` CLI: `machine_cli/terminal_fonts.py` (Guake font code replaced by Ddterm font code) and `machine_cli/mise_tools.py` (call order, so the Ddterm schema exists when the font is set).
- Tests: `tests/unit/test_terminal_fonts.py`, `tests/unit/test_package_presets.py`, `tests/integration/test_host_yaml_install.py`.
- Docs: `Readme.md` (feature `gnome`).
