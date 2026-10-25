# Host configs: context, device, features and ssh_allow_from per host.
# Filename = short hostname (`hostname -s`).
#   context: private | work        device: desktop | server (container: set by machine)
#   ansible: false                  optional; skips Ansible on hosts without root
# Feature defaults and which features a host may have: ansible/group_vars/all/features.yml
#
# Fleet (home):
#   ditschi-ThinkPad-L13-Yoga-Gen-2.yml  — this laptop (private desktop + laptop features + stylus + touch-device + sshd-home)
#   homeserver.yml                       — M720q / K3s CP (private server + sshd-home)
#   netmaster.yml                        — Pi edge (private server + sshd-home)
#   machine/ssh_keys/ditschi-ThinkPad-T470.pub — pubkey recovered from netmaster
#   A new host (e.g. the T470) gets its file from `machine setup` on that host.
#
# Work:
#   LR-C-0042H.yml — work laptop (work desktop)
#   ABTVL421.yml   — work VM (work desktop)
#
# CI host configs live in tests/hosts/ (read with MACHINE_HOSTS_DIR=tests/hosts).
#
# Flow:
#   edit here → commit/push → on host: machine update
#     → copied to ~/.local/share/machine/applied-host.yml → apply if changed
#   or from laptop: machine apply --limit <hostname>
#
# Create/update from a live host:
#   machine host save
#
# Applied copy only: ~/.local/share/machine/applied-host.yml (not in git)
#
# Homelab stacks (k3s, Traefik, Pi-hole, Influx server, …) belong in the
# separate homelab repo — Dotfiles Ansible only bootstraps the OS.
