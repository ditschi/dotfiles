# Tasks

Work only in the worktree `/home/dci2lr/dotfiles/.worktrees/work-network-autoconnect`
(branch `work-network-autoconnect`).

## 1. Password source and keyring sync

- [x] 1.1 Move the env-file parsing of `home/core/.shell/common/environment.sh` into a
  shared file sourced by the shell, and make `home/core/.local/bin/get-password` source
  it to return `$PASSWORD`, else `PASSWORD` from `~/.env`, `~/.env.host`,
  `~/.env.local`, and only then the keyring, after checking the default collection's
  `Locked` property over D-Bus and with a 5-second timeout. Verify with new tests in
  `tests/unit/test_work_net.py` using stub `secret-tool` and `busctl`: env wins over a
  differing keyring entry, env files are read without the shell environment, a locked
  keyring returns non-zero without calling `secret-tool lookup`, and values with `$`,
  quotes, `#` and spaces come out unchanged; run `tests/unit/test_update_and_env.py`
  for the unchanged shell loading.
- [x] 1.2 Create the stand-alone tool `home/work/.local/bin/work-net` (Python,
  standard library only, no import of `machine_cli`) with a shared helper that runs
  outside commands with a timeout and optional input, logging to stdout (`--verbose` /
  `WORK_NET_DEBUG=1` for debug lines), and with `work-net keyring sync`:
  when `get-password` yields an env password and the keyring is unlocked and its entry
  differs, store the env password with `secret-tool store` (secret on input). Verify
  with unit tests loading the file by path: stale entry replaced, equal entry not
  written, locked keyring untouched, a hanging stub is stopped after its timeout, the
  password never appears in process arguments or log output.

## 2. Failure guard and Kerberos refresh

- [x] 2.1 Add the shared failure guard to `work-net`
  (`~/.local/state/work-net/guard.json`, mode 600, file lock, salted fingerprint) with
  `work-net guard status|reset`:
  record outcome classes (network, rejected, locked or expired, unknown), allow at most
  2 counted failures at least 15 minutes apart, stop at once on locked or expired,
  reset on a manual run and when the password fingerprint differs from the last
  rejected one. Verify with unit tests using a fake clock for every scenario of the
  "Authentication failure guard" and "Guard reset" requirements, including concurrent
  access and file mode 600.
- [x] 2.2 Add `work-net kerberos refresh [--auto]`: parse `LC_ALL=C klist` expiry and
  renewal limit; do nothing above 2 h; `kinit -R` below 2 h when renewable; otherwise
  `kinit-pw` only when the KDC is reachable and the guard allows it; timeouts 30 s for
  `kinit`/`kinit -R` and 2 s for the KDC check (not counted); classify `kinit`
  output per the design table; run the keyring sync; record the last action in the
  state directory; notify via `notify-send` when
  available and log to the journal. Make
  `ensure-kerberos-token` a thin wrapper around it and let `kinit-pw` reset the guard
  when run without `--auto`. Verify with unit tests using stub `klist`, `kinit` and a
  fake KDC check for each "Ticket refresh" and "Bounded Kerberos calls" scenario, and
  that a German-locale `klist` output is never parsed (the command runs with `LC_ALL=C`).
- [x] 2.3 Add `work-net status` for the Kerberos part (ticket expiry and renewal limit,
  KDC, guard state and reason with the reset hint, last action). Verify with unit tests
  for the "Status view" scenario and that the output never contains the password.
- [x] 2.4 Add `work-net-kerberos.service` and `work-net-kerberos.timer` (boot + 1 min,
  every 10 min) to `home/work/.config/systemd/user/`, and make
  `machine` enable the timer only when the `kerberos` feature is selected. Verify with
  unit tests for enabling with and without the feature, and with
  `systemd-analyze --user verify` on both units.
- [x] 2.5 Remove the refresh and the cron hint from
  `home/work/.shell/work/common/environment.sh`, delete
  `home/core/.local/bin/setup-ensure-kerberos-cron`, and make `machine update` delete
  the `ensure-kerberos-token` crontab block and `~/.local/bin/ensure-kerberos-token-cron`.
  Verify with unit tests on a stub crontab (block removed, other entries kept,
  idempotent) and by timing a work shell start in the test environment without any
  `kinit` call.
- [x] 2.6 Update the Readme (`work-net`, Kerberos, password source, guard reset by a
  manual `kinit-pw`, `work-net status`, logs with `journalctl --user -u
  work-net-kerberos`, how to stop the timer). `work-net` provides no Bash or Zsh
  completion; note that in the Readme. Verify the documented commands run as written.

## 3. Validation of groups 1-2

- [x] 3.1 Run `pytest tests/unit/test_work_net.py tests/unit/test_machine_cli.py
  tests/unit/test_update_and_env.py tests/unit/test_features.py -q`
  (new tool, unit enabling and cron migration in `machine`, env loading, feature
  gating); run `pytest tests/unit -q` instead if shared CLI infrastructure changed.
  Record commands, results and why the selection covers the change.
- [x] 3.2 On the work laptop, without touching the live checkout: run the refresh from
  the worktree with a ticket that expires within 2 h and confirm `kinit -R` was used
  and no password was read; record the result.

## 4. VPN watcher

- [x] 4.1 Add `work-net vpn connect [--auto]`: set `USE_KEYRING=0` in
  `~/.wifivpn/vpn_preferences.ini`, run `sudo -n
  /opt/osd/osd-wifivpn-package/connect_vpn.sh` without `-k`, with `LC_ALL=C` and the
  `get-password` password on two input lines; classify the outcome for the guard
  (gateway unreachable = network, other failures counted) and run the Kerberos refresh
  after success. Make `vpn-pw`/`osd-vpn-connect-pw` call it, which resets the guard as
  a manual run. Verify with unit tests using a stub script for success, unreachable
  gateway, rejected password, a missing sudo rule (`sudo -n` fails), the certificate
  prompt, and a preferences file with `USE_KEYRING=1` that ends with `USE_KEYRING=0`;
  also that the script's output reaches the log line by line without the password,
  and that a hanging stub is stopped after 120 s (scaled down in the test) and not
  counted.
- [x] 4.2 Add `work-net vpn watch`: follow `gdbus monitor --system` for NetworkManager
  state changes and logind wake signals (restart the monitor when it exits), debounce
  about 3 seconds, tick every 2
  minutes; decide per the `work-vpn` spec (no network: wait; KDC reachable: refresh
  Kerberos; client running or connect in progress: grace 45 s; else connect unless the
  guard is stopped); add `work-net vpn check --dry-run` running the same decision once
  without acting. Verify with unit tests feeding recorded `gdbus` lines and a fake
  clock for every `work-vpn` scenario, an exiting monitor, and the dry-run scenario.
- [x] 4.3 Add `work-net vpn disconnect` (write the pause marker, then `sudo -n
  disconnect_vpn.sh`), define `osd-vpn-disconnect` in the work shell to call it, and
  make the watcher clear the marker at start, on a wake signal and on a manual
  `vpn-pw`. Verify with unit tests for the three "Manual disconnect pauses the
  watcher" scenarios and that a full-path `/usr/bin/osd-vpn-disconnect` is treated as
  a drop.
- [x] 4.4 Add the certificate expiry notice (read `cert.pem` with `openssl x509
  -enddate`, notify at most once per day under 20 days). Verify with unit tests for 12
  days, 25 days and a second check on the same day. Extend `work-net status` with VPN
  client, pause and certificate days left; verify with a unit test.
- [x] 4.5 Add `work-net-vpn-watch.service` (`WantedBy=` and `PartOf=graphical-session.target`,
  no stop action on the VPN)
  to `home/work/.config/systemd/user/`; make `machine` enable it only on a desktop
  device where `/usr/bin/osd-vpn-connect` exists. Verify with unit tests for the
  gating and `systemd-analyze --user verify`.
- [x] 4.6 Document the watcher in the Readme (what it does, how a manual disconnect
  pauses it, how to reset the guard, `work-net vpn check --dry-run`, logs with
  `journalctl --user -u work-net-vpn-watch`, how to stop or disable it, and the
  manual fallback `sudo -n /opt/osd/osd-wifivpn-package/disconnect_vpn.sh` plus
  `vpn-pw`). Verify the documented commands run as written.

## 5. Integration checks

- [x] 5.1 Run `pytest tests/unit -q` (the CLI, update flow and dotfile groups changed
  across modules) and `pre-commit run --files` with every changed and new path,
  including the change artifacts. Record commands and results.
- [ ] 5.2 On the work laptop with the units from the worktree: suspend for about 1
  minute and confirm the VPN recovers without a new connect; run
  `sudo -n /opt/osd/osd-wifivpn-package/disconnect_vpn.sh` (a drop) and confirm the
  watcher reconnects within about a minute; run `osd-vpn-disconnect` and confirm it
  stays disconnected until the next wake; log
  in with a locked keyring and confirm the connect uses the env password without a
  dialog; log out and confirm the VPN stays connected. Record the observed times and
  the captured `openconnect` message for a rejected password if one occurs.
- [x] 5.3 Run `openspec validate work-network-autoconnect --strict` and record the
  result.

## Implementation Validation

- Group 1: `pytest tests/unit/test_work_net.py -q`: 19 passed (get-password order,
  locked or missing keyring, timeout, value fidelity, shell loader in bash and zsh,
  keyring sync, `run` timeout and input). `pytest tests/unit/test_update_and_env.py
  tests/unit/test_zsh_handoff.py tests/unit/test_vscode_terminal_path.py
  tests/unit/test_dotfiles.py tests/unit/test_gitconfig.py -q`: 288 passed, covering
  every existing consumer that sources `environment.sh` or deploys the dotfiles.
  `pytest tests/unit/test_dotfiles.py tests/unit/test_machine_cli.py -q`: 74 passed.
  `pre-commit run --files` on all changed and new files of group 1: passed. On the
  work laptop, `env -u PASSWORD bash home/core/.local/bin/get-password` exited 0
  (output discarded); the live keyring was not written.
- Group 2: `pytest tests/unit/test_work_net.py -q`: 50 passed (guard scenarios with a
  fake clock, lock, file mode, klist parsing in the C locale, kinit classification,
  refresh scenarios, timeout not counted, status, `kinit-pw` without a terminal,
  timer content, enabling by feature, cron removal, work shell start without
  `kinit`). `machine_cli/updates.py` (setup and update path) changed, so the full
  suite ran: `pytest tests/unit -q`: 932 passed. After Black reformatted two files,
  `pytest tests/unit/test_work_net.py tests/unit/test_disk_space.py
  tests/unit/test_host_profiles.py -q`: 153 passed (the reformatted files and the
  timer-enabling consumers). `pre-commit run --files` on every changed and new path:
  passed. `systemd-analyze --user verify` on both units: only reports that
  `~/.local/bin/work-net` is not deployed yet. On the work laptop, `work-net -v
  status` from the worktree showed the real ticket, a reachable KDC and the guard.
  The docs went to `docs/features.md` with a row in the Readme table, because the
  Readme now links to docs/ for feature details. 3.2: the ticket had about 10 hours
  left, so the threshold was raised for one run with the new override
  (`WORK_NET_STATE_DIR=/tmp/wn-state WORK_NET_RENEW_BEFORE_HOURS=12 python3
  home/work/.local/bin/work-net -v kerberos refresh --auto`). The log showed only
  `klist`, the KDC check and `kinit -R` ("renewed without password"); expiry moved
  from 23:16 to 23:30, and the keyring sync found the entry up to date. A request
  through the proxy afterwards returned HTTP 200. Only the threshold differs from
  the 2-hour case, which the unit tests cover.
- Group 4 and 5: `pytest tests/unit/test_work_net.py -q`: 85 passed (VPN connect with
  a stub OSD script and stub sudo: env password, `USE_KEYRING=0`, certificate
  prompt, unreachable gateway, rejected password, missing sudo rule, 120 s timeout
  scaled down, guard; `decide` for every watcher case, debounce, 45 s grace, 2-minute
  tick, `gdbus` line parsing, monitor restart, dry run, disconnect pause and wake,
  manual connect ending the pause, aliases, certificate notice, status, watcher
  gating by device and OSD tool, unit content). Full suite `pytest tests/unit -q`:
  967 passed. `pre-commit run --files` on every changed and new path: passed after
  Black reformatted two files. `systemd-analyze --user verify` on the watcher unit:
  only reports that `~/.local/bin/work-net` is not deployed yet.
  `openspec validate work-network-autoconnect --strict`: valid. On the work laptop
  (VPN up), `work-net vpn check --dry-run` printed "would refresh the Kerberos
  ticket: work network reachable" and `work-net status` showed the running VPN
  client and 203 certificate days. 5.2 needs the units installed on the live host
  and real suspend/login cycles; it is left to the owner.
- Live install (owner approved): branch committed, rebased onto `main` and
  fast-forwarded into `/home/dci2lr/dotfiles`. `machine update --check` showed no
  steps (the commits are local, not incoming), so the two steps `machine update`
  runs for these paths were called through machine's own code: `run_dotfiles_apply()`
  and `ensure_update_timer()`. Result: both units enabled and active, the cron block
  and `setup-ensure-kerberos-cron` gone. Ansible was not needed (no system changes).
- Found live: the owner's AD account cannot read the journal, so `work-net` now also
  writes `~/.local/state/work-net/work-net.log` (owner-only, 1 MiB cap); tests keep
  their state out of the real home. `pytest tests/unit/test_work_net.py -q`: 87
  passed; pre-commit passed.
- 5.2 live (detached test unit `/tmp/wn-live-test.sh`, ends with the VPN up):
  disconnect by full path (a drop) → the watcher reconnected in 21 s; `work-net vpn
  disconnect` → still disconnected after 140 s (log: "wait: paused after a manual
  disconnect"); `work-net vpn connect` → "VPN watcher resumed (manual connect)",
  connected in 13 s. The password occurs 0 times in the log; `USE_KEYRING=0` is set.
  The watcher's own connect during the test hit the 120 s timeout because the test
  disconnected while the OSD script waited for the network; it was stopped and not
  counted, as specified. Still open: suspend and wake, login with a locked keyring,
  logout with the VPN up.

## Workflow follow-up

- Archive the change inside the worktree, then ask the owner before merging the branch
  into the live checkout and before removing the worktree.
