# Reverse tunnel for devices without dotfiles

`device-tunnel.sh` keeps a reverse SSH tunnel from a device to the jump host (oracle) open, so the device stays reachable over the jump route of `ssh-route` when Tailscale does not work. Hosts with dotfiles use the feature `ssh-tunnel` instead (see [docs/ssh.md](../../docs/ssh.md#reverse-tunnels)).

The script needs only BusyBox `sh` and an OpenSSH client from 7.4 on. It runs `ssh -N -R 127.0.0.1:<port>:localhost:22 tunnel@<jump host>` without the device's own ssh settings (`-F /dev/null`, no connection sharing), with its own key and a pinned host key of the jump host, and starts it again 30 s after every exit. Messages go to syslog with the tag `ssh-tunnel`.

| Command | Does |
|---|---|
| `device-tunnel.sh start` | starts the loop in the background unless it already runs |
| `device-tunnel.sh stop` | ends the loop and its ssh |
| `device-tunnel.sh status` | `running (pid N)` and exit 0, else exit 1 |

## Set up a device

All as root on the device. The paths are examples for a Synology NAS (DSM); on another device use a path that its updates keep and its own boot and periodic jobs.

1. Key (once): `ssh-keygen -t ed25519 -N '' -C tunnel@<alias> -f /root/.ssh/tunnel_oracle`. Commit the public key as [`machine/ssh_tunnel_keys/<alias>.pub`](../ssh_tunnel_keys/), never in `machine/ssh_keys/`.
2. Jump route in the host list (owner, Bitwarden unlocked): `machine ssh edit`, block with `HostKeyAlias <alias>` and `ProxyCommand ~/.local/bin/ssh-route %k lan=… ts=… jump=oracle:<port>`. `machine ssh add` suggests a free port. Then a manual `machine update` on oracle, which writes the key line for the port.
3. Pinned host key of the jump host, from [`machine/ssh_host_keys/privatecloud.pub`](../ssh_host_keys/privatecloud.pub), stored under the name `oracle` (the script sets `HostKeyAlias=oracle`):
   ```sh
   echo "oracle $(cut -d' ' -f1,2 privatecloud.pub)" > /root/.ssh/tunnel_known_hosts
   ```
4. Settings in `/root/.ssh/tunnel.conf` (mode 600):
   ```sh
   JUMP_HOST=<public address of oracle>
   PORT=<port of the jump route>
   KEY=/root/.ssh/tunnel_oracle
   KNOWN_HOSTS=/root/.ssh/tunnel_known_hosts
   ```
   Optional: `JUMP_PORT` (22), `JUMP_USER` (tunnel), `HOST_KEY_ALIAS` (oracle), `LOCAL_PORT` (22), `PIDFILE` (`/var/run/ssh-tunnel.pid`), `RETRY` (30), `TUNNEL_CONF` in the environment for another settings file, `TUNNEL_SHELL` for another shell to run the loop (default `/bin/sh`).
5. Script on a data volume, which system updates keep (DSM: `/volume1/scripts/ssh-tunnel/device-tunnel.sh`), mode 755.
6. Test: `/volume1/scripts/ssh-tunnel/device-tunnel.sh start`, then `… status`; on oracle `ss -ltn | grep 127.0.0.1:<port>`; from a laptop `ssh -o ProxyCommand='ssh -W localhost:<port> oracle' <alias> true`.

## Start at boot and watchdog (example: Synology DSM Task Scheduler)

Control Panel > Task Scheduler > Create, both as user `root`, both with the command `/volume1/scripts/ssh-tunnel/device-tunnel.sh start`:

- **Triggered Task > User-defined script**, event *Boot-up*: starts the tunnel after a reboot.
- **Scheduled Task > User-defined script**, daily, every 5 minutes from 00:00 to 23:55: the watchdog; starts the loop again if it died, does nothing while it runs.

## After a system update

System updates can reset `/root` (DSM does). Check that `/root/.ssh/tunnel_oracle`, `tunnel_known_hosts` and `tunnel.conf` still exist and that both tasks are still enabled; `device-tunnel.sh status` says whether the loop runs. Tailscale stays the primary path, so a broken tunnel only removes the fallback.

## Web interface over the tunnel

`ssh -L 5001:localhost:5001 <alias>` (DSM's port as an example), then open `https://localhost:5001`.
