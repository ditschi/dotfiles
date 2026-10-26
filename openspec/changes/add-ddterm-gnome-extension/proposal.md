# Proposal

## Why

Guake runs under XWayland on GNOME/Wayland and cannot read the global pointer position, so it only sometimes opens on the monitor with the cursor. The Ddterm GNOME Shell extension is a native drop-down terminal and always follows the pointer. GNOME extensions are not installable through apt or mise directly, so the setup needs an automated, root-free way to install it.

## What Changes

- Add the tool `gnome-extensions-cli` (`gext`) as a mise tool in a new dotfile group `gnome`, selected by the existing feature `gnome`.
- `machine` installs and enables these extensions with `gext` after `mise install`, per user, without root: Ddterm (`ddterm@amezin.github.com`), gTile, Clipboard Indicator, Quick Settings Audio Panel, Quick Settings Audio Devices Hider and Astra Monitor.
- Tiling Assistant ships with Ubuntu; `machine` only enables it.
- The repository carries the user's current settings of these extensions (for example Clipboard Indicator history of 150 entries) as dconf keyfiles; `machine` loads them once per host. Host-specific keys (audio device names, Astra's storage device) are not shipped.
- Guake stays installed (kept alongside Ddterm); no apt package is removed.

## Capabilities

### New Capabilities

### Modified Capabilities
- `user-tools`: user-space tools may include the GNOME extension CLI; `machine` installs and enables the listed extensions and loads their shared settings once, for hosts with the `gnome` feature.

## Impact

- `home/gnome/.config/mise/conf.d/` (new fragment), `mise.toml` (new group), `machine_cli/dotfiles.py` (group selection), `machine_cli/mise_tools.py` (extension and settings step), `home/gnome/.config/machine/dconf/*.ini` (settings), `mise/mise.lock`.
- Unit tests for group selection and the extension step; Readme/docs mention.
- Takes effect after the next GNOME Shell restart (log out/in on Wayland).
