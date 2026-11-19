# Proposal

## Why

`ssh-route` lists a jump route for homeserver (`jump=oracle:2223`) and netmaster (`jump=oracle:2224`), but on 2026-11-19 nothing listened on those ports on oracle: the hand-made `@reboot autossh` crontab entries that used to open the tunnels have exited at every boot since 2026-11-03. The owner wants the reverse tunnel to oracle as the fallback route next to Tailscale (owner decision, 2026-11-19), set up by the dotfiles instead of by hand. The future off-site backup NAS at the owner's father's will need the same fallback: its network has no port forwarding, so Tailscale is its only other remote path.

## What Changes

- New feature `jump-host` (oracle, `machine/hosts/privatecloud.yml`): a system user `tunnel` without a shell whose `authorized_keys` holds one line per device, `restrict,port-forwarding,permitlisten="127.0.0.1:<port>"`, plus an sshd `Match User tunnel` block (remote forwarding only, no TTY, `GatewayPorts no`, `ClientAliveInterval`). Devices and ports come from the jump routes in the host list `ssh/home/config` that name this host. The key is the device's file in `machine/ssh_tunnel_keys/` or, for hosts with dotfiles, its user key in `machine/ssh_keys/`.
- New feature `ssh-tunnel` (homeserver, netmaster): a systemd user unit that keeps `ssh -N -R 127.0.0.1:<port>:localhost:22 tunnel@<jump host>` open. It reads the jump host and port from the host's own block in the host list, never uses connection sharing, and restarts after every exit. No autossh.
- Devices without dotfiles: a POSIX `sh` tunnel script (BusyBox, OpenSSH 7.4) with its own key and a pinned jump host key, plus instructions for a boot task and a watchdog (example: Synology DSM Task Scheduler), in `machine/ssh_tunnel/`; device keys go to `machine/ssh_tunnel_keys/`.
- `machine ssh add` suggests the next free tunnel port from 2223 when it asks for a jump route.
- `machine/ssh_host_keys/nas-backup.pub` is renamed to `backup-nas.pub` (alias `backup-nas`, owner decision 2026-11-19).
- Once by hand: remove the `@reboot autossh` crontab entries on homeserver and netmaster, including netmaster's forward of oracle's Docker API to `0.0.0.0:9009`.

## Capabilities

### New Capabilities
- `ssh-tunnel`: reverse SSH tunnels from home hosts and devices to the jump host, both sides: the restricted tunnel user and its listeners on the jump host, the client unit on hosts with dotfiles, and the script for devices without dotfiles.

### Modified Capabilities
- `ssh-client-config`: `machine ssh add` suggests a free tunnel port for the jump route.

Affected profiles: private servers and desktops. `jump-host` is selected only on oracle (`privatecloud`); `ssh-tunnel` on homeserver and netmaster. Both are optional on private servers and desktops and excluded for work and in containers.

## Impact

- New: Ansible role `jump_host`, dotfile group with the user unit and its start script, `machine/ssh_tunnel/` (device script and README), `machine/ssh_tunnel_keys/`, feature rows in `ansible/group_vars/all/features.yml`, docs in `docs/ssh.md` and `docs/features.md`.
- Changed: `machine_cli` (tunnel list from the host list for the role, unit enabling, port suggestion in `machine ssh add`), host configs `privatecloud.yml`, `homeserver.yml`, `netmaster.yml`.
- Live hosts: oracle gets a new user and an sshd drop-in, applied only after the owner approves. homeserver and netmaster lose their crontab entries.
- Not touched: oracle's firewall (the listeners are loopback-only and port 22 is already open), the homelab repo, contabo, `ssh-route`.

Where: worktree `$(machine repo)/.worktrees/ssh-reverse-tunnel`, because the change adds dotfile groups, Ansible roles and `machine_cli` code that run on the live host.
