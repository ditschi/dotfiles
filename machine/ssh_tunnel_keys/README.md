# Tunnel keys of devices without dotfiles (spec ssh-tunnel): <alias>.pub, alias as in
# the host list (HostKeyAlias). The role jump_host allows each key on the jump host
# only for the user tunnel and only on the port of the device's jump route.
# Never put these keys in machine/ssh_keys/: that folder feeds authorized_keys of the
# fleet (sshd_home, ssh_allow_from). Hosts with dotfiles use their key from there.
# Public keys only — never commit private keys.
