# Proposal

## Why

The owner wants niri with the Dux Modular Shell (DMS) as a desktop session that `machine setup` installs when a feature is selected, including a Ghostty drop-down terminal on F12 and Mod+E for the file manager. Own niri customizations shall be distributed through the dotfiles the same way as the zsh config. Today this exists only as a manual install on the ThinkPad L13 (two duxlabs PPAs, `dms setup`, an F12 line added by hand) and cannot be reproduced on another host.

## What Changes

- New feature `niri` (optional on desktops for private and work, excluded on servers and in containers) that selects the new dotfile group `niri`.
- New Ansible role `niri_desktop`: adds the PPAs `ppa:duxlabs/dux-repo` and `ppa:duxlabs/dms` with a pinned key, installs `niri`, `dms` and `ghostty` without recommends (plus the keyring and portals DMS uses) and turns off the package's global `dms.service` enable. GDM stays the display manager; niri is chosen as a session at login (as with COSMIC).
- New `machine` step after Ansible (setup and update): on a host with the feature and DMS installed, it runs DMS's own `dms setup headless` once when no niri config exists yet (niri config, DMS includes, Ghostty config, `dms.service` with the niri session), then makes sure the niri and Ghostty configs include the repository's files.
- Dotfile group `niri`: the owner's niri customizations as one included file distributed like the zsh config (today F12 → `ghostty +toggle-quick-terminal` and Mod+E → file manager), and a Ghostty include with the quick terminal settings (top, 45 % × 85 %, autohide).
- Zsh and Bash completion for `dms` (niri and Ghostty ship their own).
- Docs: `docs/features.md`, role README.

## Capabilities

### New Capabilities
- `niri-desktop`: installing the niri session with DMS, the one-time DMS setup, and the F12 drop-down terminal.

### Modified Capabilities
- `feature-selection`: the feature `niri` and where it is offered.

## Impact

- Profiles: desktops (private and work) that select `niri`; today the ThinkPad L13, which selects the feature with this change; its hand install is taken over, because the role uses the file names of the official install. Servers and containers are unaffected.
- Code: `ansible/group_vars/all/features.yml`, `ansible/roles/niri_desktop/` (new), `ansible/workstation.yml`, `machine_cli/` (new step in setup and update), `home/niri/` (new group), `home/core/.shell/zsh/plugins.zsh`, `home/core/.shell/bash/tools.bash`, tests under `tests/unit/`, `docs/features.md`.
- New external dependency: the duxlabs PPAs (one maintainer group, key `6354D7C7146C2DD8F98892895ABFA2A5F21E824E`).
- Made in the worktree `$(machine repo)/.worktrees/niri-desktop`, because the change adds dotfiles, shell completion and Ansible behaviour that the live checkout would apply to the host at once.
