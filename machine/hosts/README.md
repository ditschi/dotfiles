# Versioned per-host answers (features, ssh_allow_from).
# Filename = short hostname (`hostname -s`).
#
# Fleet (home):
#   ditschi-ThinkPad-L13-Yoga-Gen-2.yml  — this laptop (home-laptop + stylus + sshd-home)
#   homeserver.yml                       — M720q / K3s CP (home-server + sshd-home)
#   netmaster.yml                        — Pi edge (rpi + sshd-home)
#   _example-thinkpad-copy.yml           — template for 2nd ThinkPad (see T470 key)
#   machine/ssh_keys/ditschi-ThinkPad-T470.pub — pubkey recovered from netmaster
#
# CI fixtures (do not rename):
#   ci-container.yml   — chezmoi only
#   ci-rpi-zero.yml    — ansible+apt slim
#   ci-home-laptop.yml — ansible+apt GNOME (ThinkPad mirror)
#
# Flow:
#   edit here → commit/push → on host: machine update
#     → syncs to ~/.config/machine/profile.yml → apply if changed
#   or from laptop: machine apply --limit <hostname>
#
# Create/update from a live host:
#   machine profile save
#
# Local cache only: ~/.config/machine/profile.yml (not in git)
#
# Homelab stacks (k3s, Traefik, Pi-hole, Influx server, …) belong in the
# separate homelab repo — Dotfiles Ansible only bootstraps the OS.
