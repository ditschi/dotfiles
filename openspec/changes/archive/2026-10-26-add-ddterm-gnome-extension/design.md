# Design

## Context

See proposal.md - Why. `machine` already installs mise tools per dotfile group (`machine_cli/dotfiles.py`) and runs feature-specific follow-up steps after `mise install` in `MiseToolsMixin.run_tools_install` (`machine_cli/mise_tools.py`), as for fonts and the Azure CLI. `gnome` is an existing feature that installs apt packages including guake. `gext install` writes to `~/.local/share/gnome-shell/extensions`, so no root is needed.

## Goals / Non-Goals

**Goals:**
- Idempotent, root-free install and enable of the extension set on hosts with the `gnome` feature, with the user's shared settings applied.

**Non-Goals:**
- Removing or reconfiguring Guake.
- Ddterm settings and its keybinding (can follow later through the same mechanism).
- Keeping settings in sync after the first load.

## Decisions

- **mise installs only the CLI; `machine` runs it.** mise has no hook to run a tool after install, so the extension step lives next to `link_fonts` in `mise_tools.py`. Alternative: Ansible task - rejected, it needs the Ansible run and the user's D-Bus session.
- **Tool as `pipx:gnome-extensions-cli`** in a new group `gnome` (`home/gnome/...`), selected when feature `gnome` is set, mirroring the `fonts` group. Alternative: put it in `core` - rejected, it would install on headless hosts.
- **Extension list is data, not code:** one list of UUIDs in `mise_tools.py`; each is installed with `gext install` when missing (`gext list`) and enabled. `tiling-assistant@ubuntu.com` is only enabled, never installed, because Ubuntu ships it in `/usr/share/gnome-shell/extensions`.
- **Settings as dconf keyfiles** in `home/gnome/.config/machine/dconf/<extension>.ini` (relative paths like `/org/gnome/shell/extensions/gtile/`), loaded with `dconf load`. Alternative: gsettings per key - rejected, Astra's `profiles` is a large JSON value that a keyfile handles as is.
- **Load once per host:** a marker `~/.local/state/machine/gnome-extension-settings` records the load, so later GUI changes are not overwritten. Alternative: repo wins on every update - rejected by the owner.
- **Host-specific and runtime-state keys are not shipped:** `available-*`/`excluded-*` device names of the audio devices hider, Astra `storage-main`, and Tiling Assistant `overridden-settings` and `last-version-installed`. A test fails if a shipped file contains one. Clipboard Indicator ships `history-size=150`.
- **Skip when no GNOME Shell session** (`gnome-extensions` or the Shell is absent, e.g. containers/CI): log and continue. The step is idempotent: check `gext list` first, install only if missing, then `gext enable`.
- **Pinned** through the existing lockfile, like all other tools.

## Risks / Trade-offs

- [Extension version must match the installed GNOME Shell] → `gext` picks a compatible version; failure is logged and does not fail `machine update`.
- [Shell does not load a new extension until restart on Wayland] → log a hint to log out and in.
- [pipx backend needs Python/uv via mise] → declared as dependency of the tool in the lockfile check; verified in the tests task.
- [Shipped settings can reference an extension version that differs on another host] → settings are loaded only after the extension is installed; unknown keys are ignored by dconf.
- [Tiling Assistant's `overridden-settings` are written by the extension itself when enabled] → not shipped, so the extension recreates them.
