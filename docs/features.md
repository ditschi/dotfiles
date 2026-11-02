# Features

Notes on individual features. The full list with defaults is the feature table [`ansible/group_vars/all/features.yml`](../ansible/group_vars/all/features.yml); see [host-config.md](host-config.md) for how features are selected.

Private hosts get `monitoring` (Telegraf) by default, installed from the InfluxData apt source. Config names are resolved **only** in `tasks/resolve_monitoring.yml` from the hardware and the device (not in the CLI). The inputs are the local files under `ansible/roles/monitoring/files/`; with `INFLUX_TELEGRAF_CONFIG_BASE` set, the remote Influx configs replace them. The output comes from the Bitwarden item `influxdb-telegraf-write` (see [Secrets / Bitwarden](secrets.md)). Telegraf runs only with an output; otherwise it stays stopped and `machine attention` says why. See [ansible/roles/monitoring/README.md](../ansible/roles/monitoring/README.md).

Feature `gnome`: besides the apt packages (Flameshot, extension manager), `machine` installs and enables GNOME Shell extensions without root (Ddterm, gTile, Clipboard Indicator, Quick Settings Audio Panel, Audio Devices Hider, Astra Monitor; Tiling Assistant is only enabled) with `gext` from mise. Their shared settings (`home/gnome/.config/machine/dconf/*.ini`) are loaded once per host; delete `~/.local/state/machine/gnome-extension-settings` to load them again. Log out and in afterwards. Host-specific keys (audio device names, Astra storage device) are not shipped. Ddterm is the drop-down terminal (F12); with the feature `fonts`, `machine` sets its font, like the VS Code terminal's, to FiraCode Nerd Font Mono and keeps the size. Guake is no longer installed or configured; an installed Guake is left alone (`sudo apt remove guake` removes it).

Yoga/convertible (L13): feature `stylus-touch-guard` → role `stylus_touch_guard`. Previously: [helpers-and-automation](https://github.com/ditschi/helpers-and-automation) (**archived / deprecated**).
Laptops: features `lid-switch` (closing the lid does nothing), `power-profile-switch` and `battery-charge-limit` (`battery-charge status|normal|full`) are preselected on desktops and applied only on detected laptops; `zram-swap` is preselected everywhere except containers and not applied on Raspberry Pis. Tuning for one model is a role selected by the hardware, not a feature: `thinkpad_l13_yoga_gen2` (S3 suspend, tablet on-screen keyboard), see [docs/thinkpad-l13-yoga-gen2.md](thinkpad-l13-yoga-gen2.md). Fingerprint login is set up by hand, not by `machine`: [docs/fingerprint.md](fingerprint.md). `MACHINE_HARDWARE` also accepts `l13-yoga-gen2` in tests.
COSMIC: feature `cosmic` (optional on desktops, never on servers or in containers) installs `cosmic-session` on Ubuntu 26.04+ from the unofficial PPA `ppa:hepp3n/cosmic-epoch` (key pinned in the role); GDM stays the display manager, so GNOME and COSMIC can both be chosen at login. Pop!_OS ships COSMIC, so nothing happens there. The feature also selects the dotfile group `cosmic`, whose user unit removes `DCONF_PROFILE` before a GNOME session starts: COSMIC puts it into the systemd user manager, and with linger it would otherwise survive the logout and make the next GNOME login use COSMIC's dconf database. Deselecting removes nothing; see [ansible/roles/cosmic_desktop/README.md](../ansible/roles/cosmic_desktop/README.md).
Mail: feature `thunderbird` (default on private desktops) installs Thunderbird and the mise group `home/thunderbird` with `tb` and `tb-bridge` of [thunderbird-cli](https://github.com/vitalio-sh/thunderbird-cli). The bridge extension is not installed automatically, because it accepts any local bridge, also one of another user: `machine` downloads the pinned XPI to `downloads/` in the checkout (gitignored); install it once in Thunderbird (Add-ons and Themes → gear → Install Add-on From File). Start the bridge with `tb-bridge &`, then `tb health`.

SSH home fleet: feature `sshd-home` → `authorized_keys` (`roles/sshd_home`) from [`machine/ssh_keys/`](../machine/ssh_keys/) for entries in `ssh_allow_from`.

## Kerberos ticket (work, feature `kerberos`)

The proxy needs a valid Kerberos ticket. On hosts with the feature `kerberos`, the user timer `work-net-kerberos.timer` runs `work-net kerberos refresh --auto` one minute after boot and every 10 minutes, also without a login (linger). It does nothing while the ticket is valid for more than 2 hours, renews it without a password (`kinit -R`) shortly before it expires, and requests a new one with the password only when the ticket is missing or can no longer be renewed and the KDC is reachable. Shell start no longer touches the ticket; the former cron job (`setup-ensure-kerberos-cron`) is removed by `machine update`.

- **Password:** `get-password` returns `PASSWORD` from `~/.env`, `~/.env.host`, `~/.env.local` (also in services without the shell environment). Only without it does it read the GNOME keyring, and only when the keyring is unlocked, so no unlock dialog appears. The refresh keeps the keyring entry equal to the env password while the keyring is unlocked.
- **Failure guard:** a rejected password counts; network errors and timeouts do not. After 2 rejections at least 15 minutes apart, or at once when the account is locked or the password has expired, automatic logins stop and a desktop notification says why. Fix `PASSWORD` in `~/.env` (for example with `machine env pull`), then run `kinit-pw` in a terminal: that resets the guard. A changed password also resets it.
- **Check and debug:** `work-net status` shows the ticket, the KDC, the guard and the last action; `work-net -v kerberos refresh` (or `WORK_NET_DEBUG=1`) logs every step. To try the renewal now, raise the threshold for one run: `WORK_NET_RENEW_BEFORE_HOURS=12 work-net -v kerberos refresh`. Logs: `~/.local/state/work-net/work-net.log` (the journal is not readable for AD users without the `systemd-journal` group). Stop the timer with `systemctl --user disable --now work-net-kerberos.timer`.
- Timeouts: `kinit` 30 s, keyring 5 s, KDC check 2 s. `work-net` has no Bash or Zsh completion.

## Work VPN (work desktops with the OSD VPN tool)

On a work desktop with `/usr/bin/osd-vpn-connect`, the user service `work-net-vpn-watch.service` runs `work-net vpn watch` while you are logged in to the desktop. It reacts to login, wake from sleep and network changes (and checks every 2 minutes):

- Kerberos server reachable (office LAN, USB-LAN, work Wi-Fi or VPN already up): no VPN start, only the Kerberos refresh.
- No network: waits for the next event.
- VPN client still running or a connect in progress: waits up to 45 s for its own reconnect, which is faster than a new connect; it checks every 5 s and connects at once if the client gave up.
- Otherwise it connects with `sudo -n /opt/osd/osd-wifivpn-package/connect_vpn.sh` (passwordless by the corporate sudoers) and the password from `get-password`. Before each connect it sets `USE_KEYRING=0` in `~/.wifivpn/vpn_preferences.ini`: the OSD script then uses the password from its input instead of its own keyring copy, which would be used even when stale and asks for unlocking a locked keyring. A certificate warning does not block; under 20 days a desktop notification says to run `osd-wifivpn-enroll` in the office.

Logging out stops the watcher but leaves the VPN connected, so running agents and tasks keep working. Connect attempts use the same failure guard as Kerberos; an unreachable gateway, a timeout (120 s) or a missing sudo rule are not counted.

| Command | Effect |
| --- | --- |
| `vpn-pw` / `osd-vpn-connect-pw` | `work-net vpn connect`: connect now with the env password; resets the failure guard and ends a pause |
| `osd-vpn-disconnect` | `work-net vpn disconnect`: disconnect and pause the watcher until the next login or wake |
| `work-net vpn check --dry-run` | print what the watcher would do now and why |
| `work-net status` | ticket, KDC, guard, VPN client, pause, certificate days, last action |
| `less ~/.local/state/work-net/work-net.log` | the watcher's decisions and the OSD script's output (never the password); capped at 1 MiB plus one old file |
| `systemctl --user stop work-net-vpn-watch` | stop the watcher for this session (`disable --now` permanently) |

If a connect hangs: `sudo -n /opt/osd/osd-wifivpn-package/disconnect_vpn.sh`, then `vpn-pw`. `/usr/bin/osd-vpn-connect` and `/usr/bin/osd-vpn-disconnect` by full path are the unchanged OSD tools; the watcher treats a disconnect by full path as a drop and reconnects. `osd-vpn-connect` without the pipe now asks for the password, because its keyring use is switched off; `osd-vpn-connect -k` uses the keyring copy for that run.

Working Azure CLI and GitHub CLI installations are kept, including their
authentication and package sources. Docker provisioning preserves an existing
provider instead of replacing it with `docker.io`; only a missing,
provider-compatible Compose package is added. Unmanaged providers may need
manual Compose setup. Work hosts do not preselect Docker.
