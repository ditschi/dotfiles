---
# Tailscale from Tailscale's official apt repository (pkgs.tailscale.com/stable).
# Feature: tailscale (private desktops and servers; never for work or in containers).
#
# Supported: Ubuntu and Debian (also Raspberry Pi OS), as long as the repository serves
# the host's codename (checked with <distro>/dists/<codename>/Release on every run).
# Elsewhere a warning says why nothing was installed.
#
# Installs:
#   /etc/apt/keyrings/tailscale.asc          pinned key, fingerprint
#                                            2596A99EAAB33821893C0A79458CA832957F5868
#   /etc/apt/sources.list.d/tailscale.sources deb822 source, Signed-By the key above
#   tailscale (the package enables tailscaled itself; the role does not manage it)
#
# Removes /etc/apt/sources.list.d/tailscale.list, which Tailscale's install script
# writes for the same repository; an installed package is kept.
#
# A Tailscale snap is kept: the role installs nothing next to it and says so. Move to
# the package once by hand (keeps the node name and address, no new login):
#   sudo snap stop tailscale
#   sudo install -d -m 700 /var/lib/tailscale
#   sudo cp -p /var/snap/tailscale/common/tailscaled.state /var/lib/tailscale/
#   sudo snap remove --purge tailscale
#   machine update
#
# Login is not done here: machine setup offers `sudo tailscale up`.
#
# Key rotation: apt update fails with a signature error. Get the new key from
#   https://pkgs.tailscale.com/stable/ubuntu/<codename>.noarmor.gpg
# store it ASCII-armored in files/tailscale.asc and update the fingerprint in
# tests/unit/test_tailscale.py.
#
# Deselecting the feature removes nothing. To remove Tailscale by hand:
#   sudo tailscale logout   # optional, frees the node in the tailnet
#   sudo apt remove tailscale
#   sudo rm -f /etc/apt/sources.list.d/tailscale.sources /etc/apt/keyrings/tailscale.asc
#   sudo apt update
