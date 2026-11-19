---
# Jump host for reverse SSH tunnels (spec ssh-tunnel). Feature: jump-host (oracle).
#
# Sets up:
#   user tunnel                                 system user, shell /usr/sbin/nologin
#   ~tunnel/.ssh/authorized_keys                written whole by this role, owned by root;
#                                               one line per tunnel:
#                                               restrict,port-forwarding,permitlisten="127.0.0.1:<port>" <key>
#   /etc/ssh/sshd_config.d/50-jump-host.conf    Match User tunnel: remote forwarding only,
#                                               no TTY, GatewayPorts no, ClientAlive 30 s x 3
#
# The tunnels come from machine (extra var jump_host_tunnels): every block of the host
# list file written on this host (~/.ssh/config.d/20-home, never Bitwarden) whose jump
# route names this host, with the key from machine/ssh_tunnel_keys/<alias>.pub, else
# machine/ssh_keys/<alias>.pub. jump_host_tunnels is null when there is no host list
# file or no block of this host in it (e.g. --limit with a group); the keys then stay
# as they are. Lines added by hand are removed.
#
# Adding a device: jump route in the host list (machine ssh add suggests a free port),
# its key in machine/ssh_tunnel_keys/ (devices without dotfiles), then a manual
# `machine update` on the jump host so it pulls the host list and applies the role.
#
# The listeners are loopback-only, so no firewall port is opened.
