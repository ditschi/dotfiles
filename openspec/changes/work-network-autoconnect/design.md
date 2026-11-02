# Design

## Context

See proposal.md - Why. Current state on the work laptop (verified on 2026-11-02):

- `get-password` reads the keyring (`secret-tool lookup password <user>`) first and
  `$PASSWORD` second. It is only reached through the shell environment; services do
  not load `~/.env*`. A locked keyring can open an unlock dialog.
- `ensure-kerberos-token` acts only after the ticket has expired (`klist -s`), checks
  the KDC on TCP 88 first, and is run at every work shell start and by an optional cron
  job whose crontab line hard-codes the session bus address.
- Tickets: lifetime 10 h, renewable for 24 h. `krb5.conf` has `noaddresses = true`
  (tickets do not depend on the IP address) and the cache is `FILE:/tmp/krb5cc_<uid>`
  (lost on reboot). The system locale is German, so tool messages are localised
  unless `LC_ALL=C` is set.
- The proxy `osd-proxy2` (root, port 3128) opens a password dialog when `klist -s`
  fails. Running `kinit-pw` restores proxy access without restarting the proxy.
- VPN: `osd-vpn-connect` runs `sudo /opt/osd/osd-wifivpn-package/connect_vpn.sh`.
  The corporate sudoers grants this script (and `disconnect_vpn.sh`) without a
  password. The script stops an old session, checks the machine certificate (waits for
  Enter when it expires within 20 days), checks that the gateway is reachable, takes
  the password from its own encrypted keyring entry (`osd-vpn-enc`, with `-k` or when
  `USE_KEYRING=1` in `~/.wifivpn/vpn_preferences.ini`) or else reads it from its
  input, authenticates, starts `openconnect -b` with `--force-dpd=10
  --reconnect-timeout 30`, then runs `kinit` as the user and restarts the proxy.
  The gateway session lasts 24 h. While connecting it creates `/tmp/vpn_connect_notify`.
- The VPN script's keyring fallback (read in `connect_vpn.sh`): without `-k` it takes
  `USE_KEYRING` from the preferences file; there is no option to turn the keyring off
  again. With the keyring on, it looks up `osd-vpn-enc` through the owner's session bus
  and uses the input password only when that lookup returns nothing. Then it stores
  the input password in the keyring; under `set -e` a failed store ends the script
  before authentication. A stale copy (after a password change) is non-empty, so it is
  used and rejected, and the input password is never tried. A locked keyring makes the
  lookup ask for unlocking on the owner's screen. After each authentication the script
  writes the effective `USE_KEYRING` back to the preferences file.
- The VPN machine certificate (`/opt/osd/osd-wifivpn-package/temp/certs/cert.pem`)
  is world-readable.
- The `machine` CLI already enables systemd user timers of the `systemd` group, turns
  on linger, and keeps state under `~/.local/share/machine`.

## Goals / Non-Goals

**Goals:**

- One password source for automation (the env files), usable without a login and with
  a locked keyring.
- No automatic action that can lock the AD account through a stale password.
- No root-owned code added to the managed work laptop; only the existing passwordless
  sudo rule is used.

**Non-Goals:**

- Fixing the login keyring's own unlock password after a password change (the keyring
  then needs one manual unlock with the old password; out of scope).
- Changing the OSD VPN or proxy packages.
- Automatic VPN on hosts without the OSD VPN tool, or on the remote VM.

## Decisions

### Work network = KDC reachable on TCP 88

A short TCP connect to the realm's KDC (the existing `_kdc_reachable` logic) answers
"in the work network" for office LAN, USB-LAN, work Wi-Fi and VPN alike, and is
exactly what `kinit` needs. Rejected: lists of SSIDs or interfaces (maintenance, miss
USB-LAN and docks), NetworkManager connectivity (reports "limited" in the office,
where direct internet is blocked), and ICMP ping of the domain (may be filtered).

### Event-driven watcher in the graphical session

A systemd user service, `WantedBy=` and `PartOf=graphical-session.target`, runs
`work-net vpn watch`. It follows `gdbus monitor --system` for NetworkManager
`StateChanged` and logind `PrepareForSleep(false)` (wake), debounces events for
about 3 seconds and runs one check; a 2-minute tick is the fallback. Binding to the
graphical session means it runs only while the owner is logged in and the keyring is
usually unlocked. Ending the session stops the watcher but does not disconnect the
VPN, so that running agents and tasks keep their connection (owner's decision). Rejected: NetworkManager dispatcher scripts or a system sleep hook
(root code on the managed machine, not tied to the owner's session) and a timer only
(up to minutes of delay). Reading `gdbus monitor` output avoids a new Python
dependency.

### Wait for the VPN client's own reconnect first

When the KDC is unreachable and `openconnect` is still running (`pgrep -x openconnect`)
or `/tmp/vpn_connect_notify` exists, the watcher waits up to 45 seconds after the
event: 10 s dead-peer detection plus the 30 s reconnect timeout plus a margin. Within
the 24 h gateway session this is faster than a new connect, which stops the old
session and authenticates again. After the grace period, or when no client runs, the
watcher connects.

### Non-interactive connect with the env password

The watcher runs `sudo -n /opt/osd/osd-wifivpn-package/connect_vpn.sh` with
`LC_ALL=C` and writes the password from `get-password` to its input twice: one line
for the certificate prompt, one for the password prompt; each prompt only appears when
needed and an unused line is harmless. `sudo -n` fails fast instead of prompting if
the sudoers rule ever disappears. The outcome is classified from the exit status and
output: "Unable to reach the gateway" is a network error; anything else that fails
counts for the guard. After success the watcher runs the Kerberos refresh, in case the
script's own `kinit` failed. Rejected: NetworkManager integration of the VPN tool
(`-n`; NetworkManager cannot renew the 24 h cookie).

The owner wants the VPN to use the env password, also with a locked keyring and after
a password change. The script's own fallback does not provide that (see Context: a
stale copy is used instead of the input, and a locked keyring prompts). The VPN
call therefore omits `-k`, and before each connect `work-net` sets `USE_KEYRING=0` in
`~/.wifivpn/vpn_preferences.ini`, which makes the script read the password from its
input; the script keeps that value when it saves its preferences. Rejected: keeping
the keyring copy and clearing it after a rejected password (costs one AD failure
after every password change and still prompts on a locked keyring), and toggling the
preference only while the keyring is locked (same stale-copy failure).

### A manual disconnect pauses the watcher until login or wake

When the owner disconnects by hand, the watcher does not reconnect until the next
login or wake from sleep (owner's decision). The OSD disconnect only sends SIGTERM to
`openconnect`, which looks the same to the owner's session as a drop, and its syslog
messages are not readable without the `adm` group. So the work shell defines
`osd-vpn-disconnect` as `work-net vpn disconnect`: it writes a pause marker in the
`work-net` state directory, then runs `disconnect_vpn.sh` through `sudo -n`. The
watcher clears the marker when it starts (login) and on a wake signal; a manual
`vpn-pw` clears it as well. Calling `/usr/bin/osd-vpn-disconnect` by its full path
bypasses the marker and is treated as a drop. Rejected: guessing a manual disconnect
from the absence of network or sleep events (a gateway drop looks the same).

### Kerberos refresh: renew early, password only when needed

`work-net kerberos refresh` (called by the timer, the watcher and the slimmed
`ensure-kerberos-token`) parses `LC_ALL=C klist`. More than 2 h left: nothing. Less
than 2 h left and renewable: `kinit -R` (no password, no lockout risk). Missing,
expired or not renewable: `kinit-pw`, only when the KDC is reachable and the guard
allows it. Renewing before expiry also prevents the proxy's password dialog. `kinit`
messages (with `LC_ALL=C`) are classified:

| Message | Meaning | Guard |
|---|---|---|
| `Cannot contact any KDC`, `Cannot find KDC`, `Cannot resolve network address` | network | not counted |
| `Password incorrect` | stale or wrong password | counted |
| `Client's credentials have been revoked`, `Password has expired` | locked or expired | stop at once |
| anything else | unknown | counted (conservative) |

The timer `work-net-kerberos.timer` runs at boot plus 1 minute and every 10 minutes;
linger, already enabled by `machine`, makes it run on the VM without a login. After
waking from sleep the watcher triggers the refresh, because the timer counts only
awake time.

### One shared failure guard

The guard lives in `~/.local/state/work-net/guard.json` (mode 600), protected by a
file lock because the timer, the watcher and manual runs can overlap. It stores the
count, the time of the last counted failure, a stop reason, and a salted SHA-256
fingerprint of the last rejected password with a random per-host salt. The
fingerprint lets the guard reset itself when the stored password changes; it adds no
exposure because `~/.env` already holds the password in plain text. Limits as chosen
by the owner: at most 2 counted failures, at least 15 minutes apart; then stop and
notify. A locked or expired account stops at once.

Automatic callers pass `--auto`; every other run of `kinit-pw` or `vpn-pw` is manual
and resets the guard before it runs. A manual failure is counted like any other, so
an unfixed password stops the automation again.

### Env password first, keyring kept in sync

`get-password` returns `$PASSWORD`, or `PASSWORD` parsed from `~/.env`, `~/.env.host`
and `~/.env.local` (later wins). The shell loader's parsing (plain `KEY=value` without
executing values, `${NAME}` expansion, `export` files sourced) moves into one shared
file that both the shell and `get-password` source, so the two cannot drift apart.
`work-net` gets the password only through `get-password`. Only without an env password does it read the keyring, after
checking the default collection's `Locked` property over D-Bus (no prompt) and with a
5-second timeout. The owner chose the env password to win when the two differ. The
Kerberos refresh job updates the keyring entry from the env password when the keyring
is unlocked and the entry differs (`secret-tool store`, secret on input). Reading the
env files inside the tools, instead of `EnvironmentFile=` in the units, keeps the
password out of the units' environment and avoids systemd's different quoting rules
for special characters. On the VM, too, the password comes from the env files (owner's
decision). Rejected: a keytab (an extra secret to recreate after each password
change).

### Units, gating and shell start

The units live in the `work` dotfile group. `machine` enables the Kerberos timer when
the `kerberos` feature is selected, and the VPN watcher only on a desktop device where
`/usr/bin/osd-vpn-connect` exists. Shell start keeps only a local `klist -s` status
(the OSD-managed bash prompt block already shows it); the refresh, the cron job and
the cron hint are removed without a fallback (owner's decision), because the timer and
the watcher cover every case they handled. Notifications use `notify-send` when a
session bus is available and always go to the journal.

### Runtime logic in a separate `work-net` tool, setup in `machine`

The Kerberos refresh, the failure guard and the VPN watcher live in a small
stand-alone Python tool `work-net` (standard library only) in the `work` dotfile
group. `machine` only does setup: it enables or disables the units by feature and
device and removes the old cron job. Reasons:

- `machine` is the setup and update tool; it runs on demand. `work-net` runs all the
  time and is what keeps the proxy usable. If a change in `machine_cli` breaks an
  import, `work-net` keeps working, so `git pull` and `machine update` through the proxy
  stay possible to fetch the fix.
- The logic is work-only, while `machine` serves every host; keeping it in the `work`
  group means private hosts never load it.
- Python rather than Bash because of the file-locked guard state, D-Bus line parsing,
  debouncing and date parsing; it stays testable with pytest by loading the file by
  path, as the tests already do for `machine`.
- `get-password` and `kinit-pw` stay Bash scripts (the spec requires `kinit-pw` to be
  a script usable from any context).

Rejected: putting the logic into `machine_cli` (shares its blast radius and update
cycle; its existing helpers for state, events and tests are small to reproduce), and
Bash scripts only (guard and event handling become hard to get right and to test).

### Bounded calls and diagnostics

Every outside call has a timeout so nothing can block the watcher or the timer: VPN
connect 120 s, `kinit` and `kinit -R` 30 s, keyring 5 s, KDC check 2 s. A timeout is
logged and retried on the next event or run; it is not counted by the guard, because
it says nothing about the password. If `gdbus monitor` exits, the watcher restarts it.

The OSD scripts only print to the terminal and keep no log file, so `work-net` writes
their output line by line to the journal (stdout of the unit). `work-net status` gives
one read-only view of ticket, KDC, guard, pause, VPN client, certificate and the last
action, read from the state directory and live checks. `work-net vpn check --dry-run`
runs the watcher's decision once and prints it. `--verbose` or `WORK_NET_DEBUG=1`
logs every event and decision. Nothing ever logs the password. The owner asked for
these so that a hang can be stopped by hand and problems can be found later.

## Risks / Trade-offs

- [The OSD scripts change output, paths or preferences in an update] → The watcher
  checks that the script exists; unknown failures count for the guard, so a changed
  message can stop the automation but cannot lock the account.
- [An automatic attempt with a stale password still costs one AD failure] → At most 2
  per password, 15 minutes apart, and none after a recognised lockout.
- [While the VPN is up, other local users can use it, also after the owner logged
  out] → The watcher only starts the VPN during the owner's session; the owner accepts
  that it stays up after logout so agents keep running.
- [After logout nobody restores a dropped VPN] → Accepted; the Kerberos timer keeps
  running and renews the ticket once the work network is back.
- [The owner runs `osd-vpn-connect -k` by hand] → The keyring copy is used once for
  that run; the next `work-net` connect sets `USE_KEYRING=0` again.
- [`sudo -n` stops working if the corporate sudoers rule is removed] → Fails fast,
  notifies, and the owner falls back to `osd-vpn-connect-pw`.
- [Watcher and a manual `vpn-pw` run at the same time] → The watcher skips while
  `/tmp/vpn_connect_notify` exists and takes the guard's file lock.
- [Password in process memory and on a pipe] → Never in arguments or the
  environment of the units; only on the input of `sudo`, `kinit` and `secret-tool`.
- [Captive portal or hotel Wi-Fi] → The gateway is unreachable: network error, not
  counted; retried on the next event.

## Migration Plan

1. `machine update` installs the units, enables the Kerberos timer (feature
   `kerberos`) and the watcher (desktop with OSD VPN tool), and deletes the
   `ensure-kerberos-token` block from the user crontab and the cron wrapper.
   `work-net` sets `USE_KEYRING=0` itself before each connect.
2. Rollback: `systemctl --user disable --now work-net-kerberos.timer work-net-vpn-watch.service`,
   run `osd-vpn-connect -k` once to restore `USE_KEYRING=1`, and revert the branch.

## Open Questions

- The exact `openconnect` text for a rejected VPN password is not yet captured; until
  it is, every non-network failure counts (see the table above).
