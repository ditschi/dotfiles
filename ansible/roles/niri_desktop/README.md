---
# niri session with the Dux Modular Shell (DMS) and Ghostty from the Dux PPAs
# ppa:duxlabs/dux-repo (niri, quickshell, ghostty, xwayland-satellite, ...) and
# ppa:duxlabs/dms (dms). Feature: niri (desktops only).
#
# Supported: Ubuntu, as long as both PPAs build the host's codename (checked with
# dists/<codename>/Release on every run). Elsewhere a warning says why nothing was
# installed.
#
# Installs:
#   /etc/apt/keyrings/duxlabs.asc                       pinned key (both PPAs), fingerprint
#                                                       6354D7C7146C2DD8F98892895ABFA2A5F21E824E
#   /etc/apt/sources.list.d/duxlabs-dux-repo.sources    deb822 sources, Signed-By the key above
#   /etc/apt/sources.list.d/duxlabs-dms.sources
#   niri, dms, ghostty, gnome-keyring, xdg-desktop-portal-gnome, xdg-desktop-portal-gtk
#   (without recommends: niri recommends alacritty and fuzzel, not needed here)
#
# dms.service: the dms package enables it globally for graphical-session.target, so
# it would also start in GNOME and COSMIC. The role disables that
# (systemctl --global disable dms.service); machine enables it for niri.service only.
#
# A host that added the PPAs with add-apt-repository is not changed: the role installs
# nothing and says so, because apt would see each PPA twice with another key. Remove
# those files once by hand, then run again:
#   sudo rm /etc/apt/sources.list.d/duxlabs-ubuntu-dux-repo-<codename>.sources \
#     /etc/apt/sources.list.d/duxlabs-ubuntu-dms-<codename>.sources
#
# The display manager stays as it was (GDM on Ubuntu); niri is chosen as a session at
# login. The DMS greeter is not installed.
#
# The user part is done by `machine setup` / `machine update` after Ansible (step
# `niri config`): `dms setup headless --compositor niri --terminal ghostty
# --skip-existing` once when ~/.config/niri/config.kdl is missing, the include lines for
# ~/.config/niri/dotfiles.kdl (which includes the topic files in ~/.config/niri/dotfiles/) and ~/.config/ghostty/dotfiles.ghostty (dotfile group
# niri), and `dms systemd enable` so dms.service starts with the niri session only.
# A hand-added F12 bind left in config.kdl next to the include is harmless (same bind;
# the include wins) and can be removed.
#
# The PPAs are maintained by a small group and replace Ubuntu packages such as
# quickshell. After upgrades, check where the packages come from:
#   apt policy niri dms quickshell ghostty
#
# Deselecting the feature removes nothing; the includes are optional, so the configs
# keep working without the dotfile group. To remove the PPAs and their packages by hand:
#   sudo apt install ppa-purge
#   sudo ppa-purge ppa:duxlabs/dms
#   sudo ppa-purge ppa:duxlabs/dux-repo
#   sudo rm -f /etc/apt/sources.list.d/duxlabs-dux-repo.sources \
#     /etc/apt/sources.list.d/duxlabs-dms.sources /etc/apt/keyrings/duxlabs.asc
#   sudo apt update
