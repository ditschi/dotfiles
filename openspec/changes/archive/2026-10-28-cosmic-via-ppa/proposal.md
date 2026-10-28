# Proposal

## Why

Pop!_OS ships the COSMIC desktop. The feature `cosmic` is meant to bring COSMIC to Ubuntu hosts as well. Today it installs nothing: its package list has been empty since it was added (3735b2d), and Ansible only prints a warning that names Pop!_OS. Ubuntu itself has no COSMIC packages, but the PPA `ppa:hepp3n/cosmic-epoch` builds them for the current Ubuntu LTS (26.04) and for 26.10. The feature will use that PPA.

## What Changes

- On Ubuntu 26.04 or newer, the feature `cosmic` adds the PPA `ppa:hepp3n/cosmic-epoch` as a deb822 source with a pinned signing key and installs `cosmic-session` with its recommended packages (COSMIC Term, Edit, Store, Player and so on).
- GDM stays the display manager. `cosmic-session` pulls in `cosmic-greeter`, which also provides a display manager; Ansible keeps `gdm3` as the default, so GNOME and COSMIC can both be chosen at login.
- On Pop!_OS the feature does nothing, because COSMIC is already installed.
- On older Ubuntu releases and on other distributions the feature does nothing, and Ansible prints a warning that names the reason.
- Deselecting the feature removes nothing. The PPA and the packages stay; the role README describes how to clean up with `ppa-purge`.
- The help text in the feature table and the misleading warning in `ansible/tasks/resolve_packages.yml` are replaced.
- The feature `cosmic` gets a dotfile group `cosmic` with a systemd user unit that removes `DCONF_PROFILE` from the user manager before a GNOME session starts. `start-cosmic` imports `DCONF_PROFILE=/usr/share/dconf/profile/cosmic` into the user manager, and with linger the manager keeps it after logout, so a later GNOME login reads and writes the COSMIC dconf database instead of the user's own.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `system-provisioning`: new requirement for the COSMIC session on Ubuntu from the PPA (platforms, display manager, no removal, GNOME after COSMIC without the COSMIC dconf profile), and the list of local roles gains `cosmic_desktop`.

Affected hosts: desktops (private and work) where `cosmic` is selected. `cosmic` stays optional on desktops and excluded on servers and in containers, so no host gets COSMIC without opting in.

## Impact

- Ansible: new role `ansible/roles/cosmic_desktop` (PPA source with key, debconf default for the display manager, package install, README); a new play in `ansible/workstation.yml`; the help text in `ansible/group_vars/all/features.yml`; the warning task removed from `ansible/tasks/resolve_packages.yml`.
- New third-party apt source on hosts that select `cosmic`. The PPA is unofficial and maintained by one person; it builds against Ubuntu's `-proposed` pocket.
- Dotfiles: new group `home/cosmic/` (declared in `mise.toml`) with the systemd user unit and a drop-in for `gnome-session-pre.target`; `groups: [cosmic]` in the feature table.
- Docs: Readme (role tree, feature notes), `ansible/README.md` (role table).
- Tests: unit tests for the role's platform conditions where feasible; a real COSMIC session stays outside CI (`tests-and-ci`).
