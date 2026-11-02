## Why

After switching on or waking from sleep, the work laptop should be back in the work
network as fast as possible without running `osd-vpn-connect-pw` by hand. When it is
not already in the work network (office LAN, USB-LAN, work Wi-Fi or VPN), the VPN
should start automatically, but only while the owner is logged in, so that nobody
else uses the VPN under the owner's account. After a drop the connection should come
back as well; when the VPN client recovers on its own faster than a new connect, that
is preferred.

The proxy needs a valid Kerberos ticket, independent of the VPN, on the laptop and on
the remote VM. On the VM it must stay valid even when the owner is not logged in, so
that locally running tasks such as coding agents keep reaching external resources
through the proxy. Today the ticket is only checked at shell start and by an optional
cron job, and only after it has already expired.

Both the VPN tool and `kinit` must use the owner's password from the env files, also
when the GNOME keyring is locked (for example after a password change, when the
keyring is sometimes not unlocked automatically). The keyring copy should follow that
password. A stale password must not lock the AD account: automatic attempts stop
after a small number of authentication failures, and a manual run by the owner is the
event that resets the stop.

## What Changes

- New systemd user timer that keeps the Kerberos ticket valid: renews it without a
  password (`kinit -R`) before it expires, and runs `kinit-pw` only when the ticket is
  missing or no longer renewable and the KDC is reachable. Runs with linger, so it also
  works without a login (remote VM).
- New VPN watcher on the work laptop: a systemd user service bound to the graphical
  session that reacts to login, wake from sleep and network changes. When the KDC is
  not reachable it first gives the VPN client's own reconnect a short grace period,
  then runs the VPN connect script non-interactively with the env password. Logging
  out stops the watcher but leaves the VPN connected, so running agents and tasks keep
  working. A manual `osd-vpn-disconnect` pauses the watcher until the next login or
  wake from sleep.
- The VPN tool is set to read the password from its input instead of its own stored
  copy (`USE_KEYRING=0` in `~/.wifivpn/vpn_preferences.ini`); its keyring fallback
  only covers an empty entry, not a stale or locked one.
- Shared authentication-failure guard for VPN and Kerberos: only authentication
  failures count (network errors do not), automatic attempts stop after 2 failures
  about 15 minutes apart, and a desktop notification tells the owner. A manual
  `kinit-pw` or `vpn-pw` resets the guard; so does a change of the stored password.
- `get-password` prefers the env password over a differing keyring entry, never blocks
  on a locked keyring, and updates the keyring entry from the env password when the
  keyring is unlocked.
- Notification when the VPN machine certificate expires within 20 days, instead of
  the VPN script waiting for Enter.
- **BREAKING**: the refresh at work shell start and the cron installer
  `setup-ensure-kerberos-cron` are removed; an existing cron block is deleted during
  migration. Shell start only shows the ticket status.

## Capabilities

### New Capabilities

- `work-vpn`: automatic VPN connect and reconnect on the work laptop while the owner
  is logged in - work-network detection, waiting for the VPN client's own reconnect,
  non-interactive connect, certificate expiry notice.

### Modified Capabilities

- `kerberos-tokens`: password lookup order and keyring sync, proactive ticket renewal
  by a systemd user timer, the shared authentication-failure guard, and removal of
  the cron installer and the refresh at shell start.

## Impact

- Code: `home/core/.local/bin/get-password`, `kinit-pw`, `ensure-kerberos-token`,
  removal of `setup-ensure-kerberos-cron`; `home/work/.shell/work/common/environment.sh`
  (shell start, `vpn-pw` alias); a new stand-alone tool `home/work/.local/bin/work-net`
  (Python, standard library) with its systemd user units; `machine_cli/` only for
  enabling the units and removing the cron job; unit tests under `tests/unit/`; Readme.
- Profiles: work context only. The Kerberos timer comes with the `kerberos` feature
  (work desktops and servers, including the remote VM). The VPN watcher additionally
  needs a desktop device and the OSD VPN tool (`/usr/bin/osd-vpn-connect`). Private
  hosts and containers are unchanged.
- External tools used as they are: the OSD VPN scripts under
  `/opt/osd/osd-wifivpn-package/` (passwordless `sudo` already granted by the
  corporate sudoers), `nmcli`/NetworkManager and logind D-Bus signals, `secret-tool`,
  `notify-send`.
- Work location: worktree `/home/dci2lr/dotfiles/.worktrees/work-network-autoconnect`
  on branch `work-network-autoconnect` (from `main`), because the change touches
  `home/` and `machine_cli/`, which the live checkout `/home/dci2lr/dotfiles` serves to
  the host's shell and tools.
