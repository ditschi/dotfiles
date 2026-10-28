---
# COSMIC desktop session on Ubuntu from the unofficial PPA ppa:hepp3n/cosmic-epoch.
# Feature: cosmic (desktops only). Pop!_OS ships COSMIC itself: nothing is done there.
#
# Supported: Ubuntu 26.04 and newer, as long as the PPA builds the host's codename
# (checked with dists/<codename>/Release on every run). Elsewhere a warning says why
# nothing was installed.
#
# Installs:
#   /etc/apt/keyrings/cosmic-epoch.asc          pinned key, fingerprint
#                                                EB141BFC014828F92C2EF883210C6A47471454A0
#   /etc/apt/sources.list.d/cosmic-epoch.sources deb822 source, Signed-By the key above
#   debconf-utils, cosmic-session (with recommends: COSMIC Term, Edit, Store, Player, ...)
#
# The display manager stays as it was (GDM on Ubuntu), so GNOME and COSMIC can both
# be chosen at login; cosmic-greeter is installed as a dependency but not made default.
#
# The PPA is maintained by one person and builds against Ubuntu's -proposed pocket.
# After upgrades, check that core packages still come from Ubuntu:
#   apt policy libgl1-mesa-dri libwayland-client0
#
# Deselecting the feature removes nothing. To remove COSMIC by hand:
#   sudo apt install ppa-purge
#   sudo ppa-purge ppa:hepp3n/cosmic-epoch
#   sudo rm -f /etc/apt/sources.list.d/cosmic-epoch.sources /etc/apt/keyrings/cosmic-epoch.asc
#   sudo apt update
#
# GNOME after COSMIC: start-cosmic imports DCONF_PROFILE=/usr/share/dconf/profile/cosmic
# into the systemd user manager, and with linger (enabled by machine) the manager keeps
# it after logout. A GNOME login without a reboot then reads and writes
# ~/.config/dconf/cosmic instead of ~/.config/dconf/user. The dotfile group cosmic ships
# drop-cosmic-dconf-profile.service, which gnome-session-pre.target pulls in to remove the
# variable before GNOME starts. Manual fix for a running session:
#   systemctl --user unset-environment DCONF_PROFILE   # then log out and in
# GNOME settings changed while the profile was active stay in ~/.config/dconf/cosmic;
# copy them over with dconf dump/load and a profile file that lists only that database
# (user-db:cosmic) or only user-db:user, leaving out org/gnome/desktop/interface and
# org/gnome/desktop/wm/preferences, which COSMIC sets.
