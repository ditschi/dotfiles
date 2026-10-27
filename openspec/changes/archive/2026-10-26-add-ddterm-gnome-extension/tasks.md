# Tasks

## 1. Tool and group

- [x] 1.1 Add group `gnome` (`mise.toml`, `home/gnome/.config/mise/conf.d/60-gnome.toml` with `pipx:gnome-extensions-cli`) and select it for feature `gnome` in `machine_cli/dotfiles.py`; verify with a unit test in `tests/unit` for `dotfile_groups`.
- [x] 1.2 Update `mise/mise.lock` and verify the repository check for duplicate tools passes (`pytest tests/unit -q`).

## 2. Extension step

- [x] 2.1 Add an idempotent install/enable step for Ddterm, gTile, Clipboard Indicator, Quick Settings Audio Panel, Quick Settings Audio Devices Hider and Astra Monitor to `machine_cli/mise_tools.py` (skip without GNOME Shell, log failures, hint to restart the session); verify with unit tests for installed, missing and no-GNOME cases using a fake `system.run`.
- [x] 2.2 Enable `tiling-assistant@ubuntu.com` from the system installation without installing it; verify with a unit test that no `gext install` runs for it.

## 3. Settings

- [x] 3.1 Export the current settings with `dconf dump` into `home/gnome/.config/machine/dconf/{astra-monitor,clipboard-indicator,gtile,quicksettings-audio-devices-hider,tiling-assistant}.ini`, without host-specific and runtime-state keys, and with Clipboard Indicator `history-size=150`; verify by reading the files.
- [x] 3.2 Add a unit test that fails when a shipped file contains `available-*`/`excluded-*` device lists, `storage-main`, `overridden-settings` or `last-version-installed`.
- [x] 3.3 Load the files with `dconf load` once per host after the extensions are installed, tracked by a marker under `~/.local/state/machine/`; verify with unit tests for first load and for no overwrite on a later run.
- [x] 3.4 Document the feature in Readme and the `gnome` feature text in `machine_cli/core.py`; verify `pre-commit run --all-files` passes.

## 4. Integration

- [x] 4.1 On this GNOME/Wayland host run `machine update`, log out and in, and verify Ddterm opens on the monitor with the cursor and the other extensions keep their settings.
