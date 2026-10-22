# Investigation report: env-secrets and update-mechanism

Read-only research for the investigations in the archived changes `2026-10-22-baseline-env-secrets` and `2026-10-22-baseline-update-mechanism` (design.md). Nothing was changed in code. Decisions stay with the owner.

Verification note: the unit tests could not be run here (`typer` is not installed in the system Python, so `tests/unit/test_host_profiles.py` and `test_update_and_env.py` fail on import). Findings below come from reading code and tests, not from running them. "Verified" means read in code; nothing was executed on a live host.

# Part A: env-secrets

## A1. Load order

**Findings**
- Verified (`home/dot_zsh/config/01_env.zsh`): the loop is `~/.env`, `~/.env.host`, `~/.env.local`. Each file is sourced or parsed in turn, so later files overwrite earlier ones.
- Verified (Readme, `commands`/`bitwarden.py`): `~/.env` is generated from group and profile items, `~/.env.host` from the host item, `~/.env.local` is never overwritten. The order therefore goes from general to specific to hand-written, which matches "most specific wins".
- Verified: the file-level rule means a value cannot be locked. A later file always wins, even for variables such as tokens where a local override could hide a rotated value. No per-variable rule exists.
- `tests/unit/test_update_and_env.py` (`test_env_pull_preserves_local_session_and_load_order`) covers the order.

**Suggestion:** keep the order. A per-variable rule adds complexity with no recorded case. Revisit only if a concrete conflict appears, for example a stale `~/.env.local` value shadowing a rotated token (hypothesis, not observed).

## A2. Flexible env file locations

**Findings**
- Verified: the file list is hard-coded in `01_env.zsh`; `~/.env.*` files outside the three names are ignored (spec scenario "Other env file").
- Verified: no code, test or Readme text asks for per-project files. `git-credential-env` also hard-codes `01_env.zsh` as the loader.
- Unverified: whether tools like direnv or `.env` in projects are used on any host. Project containers have their own handling (spec `project-containers`), not checked here.

**Suggestion:** do nothing until a concrete case exists. If one does, prefer an existing tool (direnv or compose `env_file`) over extending the loader, because the loader runs in every shell and in the credential helper.

## A3. Permission handling

**Findings**
- Verified (`01_env.zsh`): `stat -c %a` is compared with `-gt 600`, a numeric comparison. It prints the warning with the `chmod 600` hint and loads the file anyway.
- Verified: the check is a numeric comparison, not a bit test. Modes such as `640` or `700` warn; modes with only low bits such as `100` would not. No realistic gap, but it is not a strict group/other check.
- Verified: the warning prints on every shell start until fixed, and goes to stdout, so non-interactive shells that source the loader also print it. `git-credential-env` silences the loader (`>/dev/null 2>&1`).
- Verified (`core.write_private`, `bitwarden.py`): generated files are written through a temp file (`NamedTemporaryFile` creates mode 600) and `os.replace`, so `machine env pull` yields 600 files. Backups sit in a 700 directory. Only hand-written or copied files can be too open.
- Not present: no code path changes the mode of an existing file, and the loader never writes.

**Suggestion:** let `machine env pull` (and `machine update`, which calls it) fix the mode and say so, and keep the loader read-only with its warning. Reason: the loader runs on every shell start, including in unusual contexts, and a silent `chmod` there would surprise users; the pull command already owns these files. For `~/.env.local`, which the tool never writes, print the fix instead of changing it (hypothesis: the owner wants it untouched).

## A4. `git-credential-env`

**Findings**
- Verified (`home/dot_local/bin/executable_git-credential-env`): POSIX `sh`; rejects names that are empty, start with a digit or contain characters outside `A-Za-z0-9_`; handles only `get` (everything else exits 0 without output); reads stdin until the blank line to pick up `username`; defaults the username to `x-access-token`.
- Verified: the token comes from `printenv "$var"`. If empty and `~/.zsh/config/01_env.zsh` exists, it runs `bash -c '. "$1" >/dev/null 2>&1; printenv "$2"'` with the loader path and the variable name as arguments (no interpolation into the command string). Output of the loader is discarded.
- Verified callers: only git config, via `private.gitconfig` and `work.gitconfig` (see `baseline-git-config.md`, item 1). No other script references it.
- Environments: a terminal shell has the variable already. The fallback is for GUI-started tools (VS Code) that do not source the shell profile (per the script comment). Unverified on a live host.
- Risks: the fallback sources a user-owned file, so it trusts `~/.zsh/config/01_env.zsh` like any shell start does. The variable name is not attacker-controlled (comes from git config, validated). The loader also runs under `bash`, but `01_env.zsh` has a `[[ -n "$ZSH_VERSION" ]]` branch for this. Because the loader reads `01_env.zsh` only, files `~/.env*` load but the `BW_SESSION` or other shell setup do not matter.
- Gap: a missing token prints a stderr line and exits 0, so git falls through to the next helper or prompts (prompting is empty-helper-first, so it asks the user). No test for the GUI fallback beyond `test_gitconfig.py`.

**Suggestion:** keep the helper. Confirm each path once per host type: terminal, VS Code from the launcher, and a non-interactive run (cron/systemd). Optionally set `GIT_TERMINAL_PROMPT=0` in the update-check job (see B1) so a missing token never blocks. If the fallback is judged too risky, a smaller alternative is a loader that only parses `~/.env*` (plain `KEY=value`) instead of running the zsh file. That would remove shell execution from the credential path, but needs support for `export` lines (hypothesis).

## A5. `get-password`

**Findings**
- Verified (`home/dot_local/bin/executable_get-password`): looks up `secret-tool lookup password <user>` (user defaults to `id -un`), falls back to `$PASSWORD`, else exits 1 with a message. It never calls `bw`.
- Verified callers: `kinit-pw` (`get-password` → `kinit`), alias `update-system` in `00_alias.zsh` (pipes to `sudo -S`), alias `vpn-pw` in `01_work.zsh`. Also referenced in spec `kerberos-tokens`.
- Verified: the keyring lookup attribute is `password <user>`. The profile does not take part. `secret-tool` needs a running D-Bus/GNOME keyring, so it fails on headless hosts, where `$PASSWORD` is the only option and has to be exported from an env file.
- Verified (spec `secret-tools`, `machine_cli/bitwarden.py`): `bw` is installed to `~/.local/bin` and `BW_SESSION` is optional and not persisted unless opted in. So a Bitwarden source is only available when a session is unlocked.
- Not present: no Bitwarden item naming scheme for user passwords exists. Items today are `env/groups/<group>`, `env/hosts/<hostname>`, `ansible-vault`, SSH key items.

**Suggestion:** add `bw` as an optional first source only when `BW_SESSION` is set (no prompt, no unlock, so scripts like `kinit-pw` stay non-interactive), then keyring, then `$PASSWORD`. Use an item such as `passwords/<profile>/<user>` (naming is a hypothesis, the owner chooses). Reason: it keeps one source of truth without breaking unattended use. Keep an ordering test with stubs for `bw` and `secret-tool`. Note that `update-system` pipes the password into `sudo -S`; it exposes a plaintext password in a pipe and could be reviewed separately.

# Part B: update-mechanism

## B1. Systemd timer

**Findings**
- Verified (`home/dot_config/systemd/user/dotfiles-update-check.timer`): `OnBootSec=10m`, `OnUnitActiveSec=6h`, `Persistent=true`, `WantedBy=timers.target`. The service is `Type=oneshot` and runs `bash %h/.local/bin/dotfiles-update-check-job`.
- Verified semantics (systemd documentation, not run here): `OnUnitActiveSec` counts from the last time the service was activated, so the check runs about 6 hours after the previous run. `Persistent=true` only has an effect for `OnCalendar=` timers, so it does nothing here. If the host is off, no catch-up run happens; the first run is 10 minutes after the next boot. A suspended laptop runs it after resume only when the monotonic time has passed (unverified).
- Verified (`machine_cli/commands.py` setup): `daemon-reload` then `enable --now dotfiles-update-check.timer` when `systemctl` exists and the profile is not `container`; return codes are ignored (`check=False`). This is done in `cmd_setup`, not in `cmd_update`, so a host that never re-runs setup after the unit was added gets no timer (the unit files arrive through chezmoi).
- Verified (`dotfiles-update-check-job`): writes `~/.dotfiles-update-last-check`, exits quietly if the repo, the fetch, the branch or `origin/<branch>` is missing; creates the marker when `HEAD..origin/<branch>` has commits, otherwise deletes it. A failed fetch (offline) leaves the old marker unchanged, which is correct.
- Gaps (verified in code): the fetch has no timeout and does not set `GIT_TERMINAL_PROMPT=0`, so a private remote with a missing token could wait in a service without a terminal (unverified; git cannot prompt without a TTY and normally fails). The repo path is `$DOTFILES_REPO` or `~/dotfiles`; a checkout elsewhere is silently never checked. The marker is created even for a checkout with local-only commits only if upstream is ahead; diverged history also counts as "update available", but `machine update` then stops (spec "Diverged history").
- Hosts without user systemd (containers, WSL without systemd, SSH-only sessions without linger): no timer; the hint never appears. On servers, user timers need `loginctl enable-linger` to run when nobody is logged in. Nothing in the repo was found that enables linger (grep over `ansible/` and `home/` for `linger` was not done, so unverified).
- Tests: no test covers the units or the job script.

**Suggestion:** keep the timer and interval; 6 hours is enough for a hint. Add `GIT_TERMINAL_PROMPT=0` to the job, document that `Persistent` does nothing, and decide whether linger is needed on the home server. Test the job script against a local bare repo (cheap, no system state). Reason: the hint is only as fresh as the timer, and the job is small enough to test directly.

## B2. When Ansible runs

**Findings**
- Verified (`commands.py::cmd_update`): the apply runs only when `sync_host_profile_from_repo()` reports a change in the host profile or when `--system` is passed. Otherwise `update finished`. chezmoi apply and `env pull` always run.
- Verified: package or role changes in the repo (not the host profile) do not trigger Ansible; they wait until `--system` or a profile edit. The Readme says the same ("apply on drift", `--system` for packages).
- Tests (`test_update_and_env.py`): profile unchanged skips apply, profile changed applies, `--system` applies.

Approaches:
1. Always run on update. Pros: hosts never drift, simple mental model. Cons: slow (apt, downloads), needs sudo each time, a network or apt failure breaks a routine update.
2. On request only (today's `--system`). Pros: fast and predictable. Cons: system state drifts silently; nothing tells you that roles changed.
3. On relevant change: compare `ansible/` (and `machine/hosts/<host>`) between old and new `HEAD` with `git diff --name-only`; apply only if those paths changed, or print a hint "ansible/ changed: run machine update --system". Pros: automatic when it matters, cheap otherwise. Cons: path matching can miss shared inputs (for example files under `home/` used by roles); needs a rule list.

**Suggestion:** option 3, starting with the hint-only variant (no automatic sudo run). Reason: keeps updates explicit (spec "Explicit update") and fixes the silent drift without surprising slow runs.

## B3. Restore after a failed apply

**Findings**
- Verified (`commands.py::cmd_apply`): local runs back up `profile.yml` to `<state_dir>/profile-backup/profile.<stamp>.yml`, sync the repo host file into it, then run `ensure_bootstrap_tools`, Ansible and `apply_authorized_keys_from_bw`, then `health_check_after_apply`. On `CalledProcessError` or `RuntimeError` it restores the backup (`restore_local_profile` copies it, sets mode 600, rewrites the chezmoi config), and re-runs Ansible only if the profile had changed; otherwise it logs "not retrying" and exits 1. The Readme (line ~180) describes the same.
- Verified: what is restored is only `profile.yml` and the chezmoi config derived from it. Ansible changes already made (packages, files, services) are not undone; the second Ansible run converges the host to the old profile only as far as roles are idempotent and reversible (removed features may leave packages behind; unverified). Remote runs (`--limit`) never revert.
- Verified gap: `health_check_after_apply` in `machine_cli/tools.py` sets `ok = True` and never changes it; the telegraf check only logs a warning. So the health check can never fail in production, and the "health check failed" revert path is exercised only by a test that stubs it to `False`. Code comments explain that the previous stricter checks rolled back successful applies.
- Verified gap: a failing `apply_authorized_keys_from_bw` is not caught unless it raises `CalledProcessError`; other exceptions (for example from `bw`) propagate without restore (unverified, depends on the implementation of that function).
- Verified: the backup is made before `sync_host_profile_from_repo`, but `cmd_update` already called `sync_host_profile_from_repo()` before `cmd_apply`, so in the update flow the profile is already the new one when `cmd_apply` backs it up. The backup then equals the new profile, and `profile_changed` in `cmd_apply` is False (the sync is a no-op second time). Result: after `machine update` with a changed profile and a failing Ansible, the "restore" copies the new profile over itself and no revert run happens. Only `machine apply` run directly reverts as documented. This is a reading of the code; not executed.
- Tests: `test_host_profiles.py` has `test_apply_reverts_on_health_check_failure` (two Ansible runs, old profile restored) and a test that an unchanged profile is not retried (`calls == ["ansible"]`, original bytes kept). There is no test through `cmd_update`.

**Suggestion:** treat the update-flow finding as a likely bug and confirm it with a unit test that calls `cmd_update` with a changed host file and a failing Ansible stub. If confirmed, back up before the sync in `cmd_update` and pass that backup (and the changed flag) into `cmd_apply`. Also decide whether the health check should be able to fail, or drop the revert claim for it from the docs. Reason: the documented safety net does not hold for the main entry point.

## B4. Layout migration offer

**Findings**
- Verified (`migration.py::needs_layout_migration`, `handle_layout_gate`): `cmd_update` calls the gate twice (before and after `git pull`). It looks for root-symlink names in `$HOME` pointing into the repo, and a missing chezmoi config. Non-interactive runs abort with a hint; interactive runs offer migration.
- Verified: `machine setup` also uses the legacy rollback and migration state (`backup_migration_state`, `write_rollback_script`); `cmd_migrate`, `cmd_rollback` and `preserve_git_host_settings` are tied into `cmd_setup`. The Readme (lines ~381-430) documents the migration for hosts "not yet on the chezmoi layout".
- Verified: tests in `test_machine_cli.py` cover detection and the migration (`test_needs_layout_migration_detects_old_root_symlink`, `test_migration_*`).
- Unverified: that all hosts are migrated (owner statement). Hosts in `machine/hosts/` are 9 files; a host that is rarely updated could still be on the old layout.

**Suggestion:** after the owner confirms every host (check `~/.config/chezmoi` and `~/.zshrc` link target on each), remove only the double gate call in `cmd_update`, and keep `machine migrate` and `rollback` as a documented emergency path for one release. Reason: the gate does file-system checks on each update, but `migrate` is the only tool for a late host, so deleting everything at once is irreversible for rarely used hosts.

## B5. Reload after a successful update

**Findings**
- Verified: `cmd_update` ends with `update finished` (or `apply finished`). Nothing prints a reload hint or starts a shell. The shell health-check cache is invalidated when dotfiles are updated (Readme line ~51); that concerns bash→zsh handoff, not the current shell.
- A process cannot change its parent shell's environment. Only a shell function or `exec zsh` in the shell itself can reload.
- Verified: `update-dotfiles` and `dotfiles-update` are helpers delegating to `machine update` (spec `update-flow`). If they are shell functions/aliases in `00_alias.zsh` they could reload after success; if they are scripts, they cannot (not checked which).

Approaches:
1. Print "run `exec zsh` to reload" when files under `home/dot_zsh` changed. Pros: trivial and safe. Cons: manual.
2. Make the shell helper a zsh function that runs `machine update` and, on success, `exec zsh`. Pros: automatic. Cons: kills the current session state (jobs, history not yet saved), surprising in scripts.
3. Only reload for interactive, tty shells and when config changed, asking first.

**Suggestion:** option 1, printed only when zsh-related files changed in the pulled range. Reason: cheap, no surprise, and no risk to running jobs.

## B6. Syncing local changes across machines

**Findings**
- Verified: the repo is the single source (`Readme`: "Git is the source of truth"). `machine commit` and `machine push` exist (`commands.py`), and `machine update` refuses dirty trees without `--force`. Local edits outside the checkout are not detected.
- What can change outside the checkout (verified from code/docs): `~/.gitconfig.local`, `~/.env.local`, `~/.zsh/config` files if not symlinks (symlink mode means edits through the link land in the repo), `~/.local/state/machine/profile.yml` (synced from `machine/hosts/<host>.yml` on update), `~/.ssh` material, and files modified by Ansible roles. Generated `~/.env` and `~/.env.host` come from Bitwarden.
- Unverified: whether other hosts edit non-symlinked copies.

Approaches:
1. Git only (today): edit in the checkout, `machine commit`, `machine push`, others `machine update`. Pros: history, review, conflict handling exists. Cons: host-local files stay out; needs discipline.
2. Add a drift report (`machine status` lists differences between managed targets and the repo with `chezmoi diff`, and files outside). Pros: makes edits visible without moving them. Cons: informative only.
3. A file-sync tool (Syncthing, rsync) for selected paths. Pros: continuous. Cons: no history, silent overwrites, secrets in transit, conflicts decided by timestamp.
4. Move host-local data into Bitwarden items (like env files today). Pros: already built for secrets. Cons: not suited to larger or binary files.

**Suggestion:** option 1 plus 2. Reason: chezmoi already knows what it manages, so `chezmoi diff` or `chezmoi verify` gives the list for the first step of the investigation; decide on more only if that list shows real losses.

## B7. Automatic rollout

**Findings**
- Verified: `update-flow` requires that nothing is applied without the user running the command, so any automation changes a spec requirement. The timer today only fetches and sets a marker.
- Verified safeguards already in `machine update`: dirty-tree refusal, `--ff-only` pull, diverged-history stop, profile revert on apply failure (see B3 for its limits). Missing: pre-update snapshot of the previous `HEAD` for rollback, and a record of the last good commit.
- Unverified: which hosts are always on and unattended (the home server, per the design text for remote updates).

Approaches:
1. Timer runs `machine update` (user unit) on selected hosts only, for config only (no `--system`). Pros: little new code; fast-forward only, no sudo. Cons: changed dotfiles apply under a running session without notice; a bad commit spreads to all opted-in hosts at once.
2. Staged rollout with a git channel: hosts follow a `stable` branch/tag that is moved by hand after the canary host runs the new commit. Pros: a bad commit stops at the canary. Cons: one extra manual step; branch management.
3. Notify only (today) plus a one-line approval, for example `machine update --yes` from a notification or mobile ssh. Pros: keeps the spec as is. Cons: not automatic.

**Suggestion:** option 2 with option 1 for the opt-in hosts, config-only at first, and record the previous `HEAD` in the state directory so `machine update --rollback` can reset to it. Reason: it addresses "must not overwrite local work" with the existing clean-tree and fast-forward rules, and limits the blast radius of one bad commit. Needs an `update-flow` spec change first.

## B8. Remote updates

**Findings**
- Verified: `machine apply --limit <host>` runs Ansible over SSH for a profile file in `machine/hosts/` with no auto-revert (`cmd_apply`, remote branch). That applies system state, but does not pull the checkout or run chezmoi on the target.
- Verified: `homeserver.yml` and an SSH public key for it exist under `machine/`. Whether the server is reachable over Tailscale/SSH from the other hosts was not checked (the setup has `maybe_tailscale_login`).

Approaches:
1. SSH from a workstation: `ssh homeserver 'machine update --system'` (a small `machine update --host <name>` wrapper). Pros: no new service; reuses the SSH keys; output visible. Cons: needs the sudo password or a non-interactive rule; the workstation must be on.
2. Pull-based on the server: the timer from B1 plus B7 option 1 (config only) and a manual `--system`. Pros: no inbound access needed. Cons: not instant; system changes still need a login.
3. Ansible `ansible-pull` or a webhook that triggers an update. Pros: push-like speed with pull-style security. Cons: new component, secrets for the vault password, more to maintain.

**Suggestion:** option 1 first (a thin wrapper over SSH), later option 2 for the config-only part. Reason: it needs no new software. Avoid webhooks until there is a reason, because they add an inbound path to a host that holds secrets.
