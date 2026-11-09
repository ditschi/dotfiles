# Public keys for ansible role sshd_home (authorized_keys via ssh_allow_from).
# machine setup / machine ssh sync|rotate write <hostname>.pub here for home hosts.
# Filename = hostname entry in machine/hosts/*/ssh_allow_from (no path chars).
# Public keys only — never commit private keys.
# homelab-ci.pub: public half of the homelab CI secret COMPOSE_SSH_KEY; not a host.
#   The role homelab_node allows it for the deploy user only for `homelab deploy <sha>`.
