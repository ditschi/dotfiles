# Design

## Context

See proposal.md for the motivation. State found on 2026-11-19 (read-only checks from homeserver; a second session "Oracle-Tunnel Setup fehlend" found the cause of the failure):

- **Clients today.** homeserver and netmaster each have a `ditschi` crontab entry `@reboot autossh -fNC -R 2223:localhost:22 oracle` (netmaster: 2224). It connects through the `oracle` alias as the full account `ubuntu@oracle` with the host's user key; there is no restricted user and no `permitlisten`. Neither process ran on 2026-11-19. Cause: the shared SSH defaults set `ControlMaster auto` and `ControlPersist 10m` (see `ssh-client-config`), so ssh turns into a background master and its foreground exits with status 0. autossh reads that as an intended end and quits. The homeserver syslog shows `ssh exited with status 0; autossh exiting` at every daily reboot since 2026-11-03 (last: 2026-11-15 04:02). The tunnels last worked on 2026-10-31, before the shared config replaced the hand-written one.
- **netmaster also has** `@reboot autossh -M 0 -N -L 0.0.0.0:9009:localhost:2375 oracle`. Port 2375 on oracle is `dockerd`'s unauthenticated API on loopback; this entry would expose it to the home LAN. It did not run on 2026-11-19.
- **oracle** (`privatecloud`, Ubuntu 22.04, OpenSSH 8.9, dotfiles as `ubuntu`, host config without `sshd-home`): sshd listens on 22 with password and keyboard-interactive login off, `GatewayPorts no`, `AllowTcpForwarding yes`, `PermitListen any`, `ClientAliveInterval 0`. No drop-in in `/etc/ssh/sshd_config.d/`. Users with a shell: `ubuntu` (10 keys in `authorized_keys`, none with options) and `opc`. Nothing listens on 22xx. The firewall (iptables from the image plus the homelab `host-firewall.service`) accepts 22 from everywhere and loopback, so loopback listeners need no rule. `ubuntu`'s host list `~/.ssh/config.d/20-home` (written 2026-10-31) holds the jump routes of homeserver (2223) and netmaster (2224).
- **homeserver** (Ubuntu, systemd) and **netmaster** (Debian 13, systemd 257): `autossh` installed, linger enabled for `ditschi`, user units of the `systemd` group active. Both have the features `sshd-home` and `tailscale`.
- **backup-nas** (Synology DS212+, armv5tel, DSM 6.2.4, BusyBox, OpenSSH 7.4 client, no systemd, no autossh; Tailscale 1.58.2): no tunnel key or script yet. It moves to a network without port forwarding, possibly CGNAT/DS-Lite. Its alias in the host list is still `nas-backup` with `IdentityFile ~/.ssh/id_rsa_nas`; its host key is `machine/ssh_host_keys/nas-backup.pub` (first use on 2026-10-31). The homelab session "Synology Offsite-Backup Konfiguration" sets up the NAS and creates its tunnel key `/root/.ssh/tunnel_oracle`.
- **Host list.** The jump routes and their ports live only in the Bitwarden note `ssh/home/config` and the file each host writes from it (`ssh-client-config`). That change recorded that addresses, users and tunnel ports stay out of the public repository.

## Goals / Non-Goals

**Goals:**
- The jump route of every home host in the host list works whenever the host is online.
- One source for which device listens on which port: the host list.
- A stolen tunnel key opens nothing but its own loopback port on oracle.

**Non-Goals:**
- Changes to `ssh-route` or Tailscale.
- Tunnels for other protocols (the TeddyCloud port 2443 from homelab `docs/teddycloud-remote.md`).
- Monitoring of the tunnel ports.
- oracle's firewall, the homelab repo, contabo.
- Removing the unrestricted keys of homeserver and netmaster from `ubuntu@oracle`; other jobs use them (e.g. homelab `pull-oracle-repo`).

## Decisions

**Two features, server and client (owner decision, 2026-11-19).** `jump-host` on oracle sets up the tunnel user, its keys and the sshd block; `ssh-tunnel` on homeserver and netmaster runs the client. Rejected: one feature that detects whether the host is the jump host (hidden behaviour from one name); the server side inside `sshd-home` (that role fills `ubuntu`'s keys for logins, a different job).

**Ports only in the host list (owner decision, 2026-11-19).** The jump host takes the tunnels from the jump routes in its written host list that name itself, recognised as `ssh-route` recognises the jump host (hostname or `HostKeyAlias`). The client takes its port from its own block. So `ssh-route` and the tunnel always agree, and the recorded decision to keep ports out of the repository holds. `machine` parses the host list (the existing block parser) and hands the tunnel list to the role as an extra-vars file; the role does not parse ssh config. Trade-off: a new device needs the host list edit, its key in Git and a manual update on oracle (the background update reads the written file and never pulls the note). Rejected: ports in `machine/hosts/*.yml` (public repository, and a second copy of the port next to the host list).

**Existing user key on hosts with dotfiles (owner decision, 2026-11-19).** The tunnel line for homeserver and netmaster uses `machine/ssh_keys/<host>.pub`. The restriction sits on the line in `tunnel`'s `authorized_keys`, so the same key stays unrestricted only where it already was. Rejected: an extra tunnel key per host (key generation, Bitwarden backup and a repository file for little gain, since whoever holds the host holds both keys).

**Device keys in their own folder (owner decision, 2026-11-19).** Keys of devices without dotfiles go to `machine/ssh_tunnel_keys/<alias>.pub`. `sshd_home` and the `ssh_allow_from` offer read only `machine/ssh_keys/`, so a device key never turns into a login on the fleet.

**Plain `ssh` under systemd instead of autossh (owner decision, 2026-11-19).** A user unit runs `ssh -N` with `ControlMaster=no`, `ControlPath=none`, `ExitOnForwardFailure=yes`, `ServerAliveInterval=30`, `ServerAliveCountMax=3`, `BatchMode=yes`, `Restart=always` and a 30 s delay (a user unit cannot order itself after the system's `network-online.target`; until the network is up, ssh fails and the next attempt follows 30 s later). systemd restarts it whatever the exit status, which removes the failure above; ServerAlive detects a dead connection, which autossh's own monitor did before OpenSSH had it. Status and log are in `systemctl --user status` and the journal. Rejected: autossh `-M 0` under systemd (works the same, one more package, no gain). The unit starts a small script from the dotfiles that reads the port with `ssh -G` and `exec`s ssh; when the host has no jump route it exits with 78, which the unit lists in `RestartPreventExitStatus`, so a missing entry does not loop. The unit is a user unit because the key belongs to `ditschi`; linger (already on, and ensured by `machine update`) starts it at boot. It is enabled and disabled with the feature like the work-net units.

**sshd block for `tunnel`.** A drop-in `/etc/ssh/sshd_config.d/50-jump-host.conf` with `Match User tunnel`: `AllowTcpForwarding remote`, `GatewayPorts no`, `PermitTTY no`, `X11Forwarding no`, `AllowAgentForwarding no`, `AllowStreamLocalForwarding no`, `ClientAliveInterval 30`, `ClientAliveCountMax 3`, `ForceCommand /usr/sbin/nologin`. The key options (`restrict,port-forwarding,permitlisten=`) repeat the limits per key, so a mistake in one layer does not open the other. ClientAlive frees the port of a dead session within about 90 s, so the client's next attempt can listen again. The role validates with `sshd -t` and reloads like `sshd_home` (socket-activated sshd included). The user `tunnel` is a system user with `/usr/sbin/nologin` and a root-owned `authorized_keys` (the role writes it whole).

**Device script in `machine/ssh_tunnel/`.** `machine/ssh_tunnel/device-tunnel.sh` (POSIX sh, options up to OpenSSH 7.4) reads `JUMP_HOST`, `PORT`, `KEY` and `KNOWN_HOSTS` from a config file on the device (default `/root/.ssh/tunnel.conf`), so no address goes into the repository. `start` checks a PID file and, if no tunnel runs, starts a background loop: `ssh -N -R 127.0.0.1:$PORT:localhost:22` with the same options as the unit plus `UserKnownHostsFile=$KNOWN_HOSTS`, `HostKeyAlias=oracle`, `StrictHostKeyChecking=yes`, `IdentitiesOnly=yes`, and 30 s between attempts, logging to syslog through `logger`. The DSM boot task and a watchdog task every 5 minutes both run `start`. `machine/ssh_tunnel/README.md` holds the DSM steps, the config file and how to pin oracle's host key. The homelab session copies the script to the NAS and sets it up.

**`machine ssh add` suggests the port.** It suggests the lowest free port from 2223 among the jump routes to that jump host, so ports do not collide without a separate registry.

**Private hosts, also desktops (owner decision, 2026-11-19).** Both features are optional on private servers and desktops, so a laptop can also be reached through oracle while away; they are excluded for work and in containers.

**The off-site NAS is a later device (owner decision, 2026-11-19).** The off-site backup goes to a new UGREEN DXP4800 Plus (UGOS Pro, Debian-based, x86) instead of the DS212+ `backup-nas`; the DS212+ is retired. Its tunnel follows once the device is set up, on port 2225, as an `ssh-tunnel` host if it runs the dotfiles, otherwise with the device script. The DS212+ tunnel key is not used. The device script stays, with instructions for devices without dotfiles in general; the host key `backup-nas.pub` stays while the DS212+ still runs.

**Other tunnels later through the same role (owner decision, 2026-11-19).** `tunnel`'s `authorized_keys` has one owner, the role. A tunnel that is not an SSH host, such as TeddyCloud's 2443, gets its line through this role in a later change, once DS-Lite at the other end is confirmed; nobody adds lines by hand or from the homelab repo.

## Risks / Trade-offs

- [The host list on oracle is stale, so a new device is missing] → a manual `machine update` (or `machine ssh pull` and `machine apply`) on oracle after the host list edit; the docs and the `machine ssh add` output name it.
- [Device key and host list disagree (key committed, no jump route, or the other way)] → the role warns about a jump route without a key; a key without a route is unused.
- [A dead session still holds the port after a client reconnects] → ClientAlive ends it within about 90 s; `ExitOnForwardFailure` makes the client retry instead of running without the forward.
- [Everyone with a shell on oracle can connect to the loopback tunnel ports] → the target still checks its own host key and user key; only `ubuntu` and `opc` have shells on oracle.
- [System updates on a device remove the script or its jobs] → the README says what to check after an update; Tailscale stays the primary path.
- [The background update reads the host list file, which `ssh-client-config` keeps away from the background update] → it reads only the file already written on the host, never the Bitwarden note, which is the part that requirement protects.

## Migration Plan

1. Merge and push; on oracle, after the owner approves the live change: `machine update` (manual) applies `jump-host`. Check: `getent passwd tunnel`, `sudo sshd -T -C user=tunnel,host=x,addr=127.0.0.1 | grep -i -E 'allowtcpforwarding|permittty|clientalive'`, `sudo cat ~tunnel/.ssh/authorized_keys` shows two lines (2223, 2224).
2. On homeserver and netmaster, once by hand: `crontab -e` and delete the `@reboot autossh` lines (netmaster: both, including `-L 0.0.0.0:9009:localhost:2375`); stop running autossh processes if any (`pkill -u ditschi autossh`). Then `machine update` enables the unit. Check: `systemctl --user status ssh-tunnel`, and on oracle `ss -ltn | grep 127.0.0.1:222`. From a host outside the home network with Tailscale logged out: `ssh homeserver` uses the jump route.
3. The DS212+ `backup-nas` gets no tunnel (see Decisions). `git mv machine/ssh_host_keys/nas-backup.pub machine/ssh_host_keys/backup-nas.pub` keeps its host key under the new alias until it is retired; then delete the file and run `machine ssh remove backup-nas`. The off-site NAS gets its tunnel in a later change.
4. `openspec/backlog.md`: entry for monitoring the tunnel ports on oracle (owner decision, 2026-11-19), e.g. once `monitoring` reaches oracle.
5. Rollback: remove the features from the host configs; on oracle `userdel tunnel` and delete the drop-in, then `systemctl reload ssh`; on the clients `systemctl --user disable --now ssh-tunnel`. The crontab entries are not restored (they no longer worked).
