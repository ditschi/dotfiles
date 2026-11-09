# Design

## Context

See proposal.md for the motivation and the delta specs for the required behaviour.

Current state of `home/core/.shell/bash/zsh-health.bash`:

- `_zhc_run_checks <zsh>` checks that zsh is executable and that `~/.zshrc` and `~/.shell/zsh/init.zsh` are readable, then runs one trial `DOTFILES_ZSH_CHECK=1 TERM=… setsid -w timeout -k 1 ${DOTFILES_ZSH_CHECK_TIMEOUT:-60} zsh -l -i -c 'print -r -- "DOTFILES_ZSH_LOADED=… DOTFILES_ZSH_DEFERRED_LOADED=…"'` with stdin `/dev/null` and stdout/stderr in temporary files. It traps `INT` while it waits and kills the trial's process group on Ctrl-C. It prints one reason and returns 1, or returns 0. Order of reasons: interrupted, timed out (rc 124/137), exit code, non-empty stderr (`zsh printed errors on startup: <first line>`), missing `DOTFILES_ZSH_LOADED=1`, missing `DOTFILES_ZSH_DEFERRED_LOADED=1`.
- `dotfiles_zsh_handoff_ok` skips fresh hosts (no antidote or no generated plugin file), reads the state file `${XDG_STATE_HOME:-~/.local/state}/dotfiles/zsh-handoff` (`status`, `zsh`, `marker`, `reason`), reuses it while the zsh path and the pending-update marker match and `_zhc_stale` finds no watched file newer than the state file, and otherwise runs `_zhc_run_checks`. Timeouts and interrupts are not cached. A failure prints `zsh handoff skipped: <reason> (fix it, then run: zsh-recheck)` on stderr.
- `zsh-recheck` removes the state file, runs the check and prints `zsh handoff check passed` on success.
- `machine` calls `_zhc_run_checks` through `zsh_health_failure()` in `machine_cli/auto_update.py`, which returns stdout as the reason when the exit status is non-zero. Callers: the automatic update (`_auto_steps`, reverts on failure, event code `zsh-unhealthy`), the manual update (`updates.py`, `runner.fail` plus needs-attention, no revert), and the post-apply health check (`tools.py`, which matches `zsh printed errors on startup: mise WARN missing: ` to run `mise install` once and otherwise restores).

zsh startup files (zsh 5.9, `man zshall`, section STARTUP/SHUTDOWN FILES, checked on this host with Ubuntu's zsh 5.9): `/etc/zsh/zshenv` is read first and "this cannot be overridden". The option `GLOBAL_RCS` (set by default; `-d` or `+o GLOBAL_RCS` unsets it) controls the remaining global files; once it is unset, the following global files are not read: `/etc/zsh/zprofile`, `/etc/zsh/zshrc`, `/etc/zsh/zlogin` (and `/etc/zsh/zlogout` on exit). The user files `~/.zshenv`, `~/.zprofile`, `~/.zshrc`, `~/.zlogin` are still read. The manual also notes that a file in `$ZDOTDIR` can re-enable `GLOBAL_RCS`; the dotfiles do not. Verified: `zsh -l -i +o GLOBAL_RCS -c 'setopt'` lists `noglobalrcs`, and the `key` array that Ubuntu's `/etc/zsh/zshrc` defines is absent.

## Goals / Non-Goals

**Goals:**
- Dotfile errors keep failing the check, including error output while the markers are set.
- Output from global startup files other than `/etc/zsh/zshenv` no longer keeps the user in bash; a real breakage there (non-zero exit, incomplete load, hang) still does.
- No extra cost on a cached start.

**Non-Goals:**
- Pattern allowlists or any company strings in the repository.
- Fixing or silencing the company hooks.
- Changing the cache keys, the fresh-host skip, the timeout length or the detached trial start (`2026-11-02-zsh-check-no-lockout`).
- Output from `/etc/zsh/zshenv`: zsh cannot skip it, so it stays a strict failure.

## Decisions

1. **Two trial runs, strict first.** The check first runs `zsh -l -i +o GLOBAL_RCS -c …` with exactly today's environment, detachment, timeout and interrupt handling, and today's failure rules (stderr, exit, markers, timeout). Strict checking catches real dotfile errors, such as an unguarded `. "$HOME/.cargo/env"` in `~/.zshenv` that writes to stderr on hosts without cargo while the markers are set. Only when it passes, the full run `zsh -l -i -c …` follows; there, exit status, markers and timeout count as today, and stderr does not. The global files are owned by the company on work hosts and cannot be fixed without root, so their output must not lock the user into the bash fallback.
   - Rejected: tolerating all stderr when the markers are set, because it misses real breakage such as the cargo example.
   - Rejected: pattern allowlists, because they are fragile and would put company strings into the repository.
   - Rejected as the primary approach: not caching stderr-only failures, because it costs one check per login for as long as the noise lasts.
2. **Full run's stderr becomes a warning.** When the full run passes but wrote to stderr, the outcome is a pass with a warning: the first stderr line, prefixed so that it does not match the strict reason (for example `zsh startup printed output with the system startup files: <line>`). The strict reason text stays `zsh printed errors on startup: <line>`, so the `mise WARN missing` handling in `tools.py` keeps working.
3. **Interface of `_zhc_run_checks`.** The exit status keeps its meaning (0 pass, 1 fail, reason on stdout). On a pass with a warning it prints the warning line on stdout with a fixed prefix (for example `warning: …`) and returns 0. `machine`'s `zsh_health_failure()` stays the failure query (empty on a pass, also with a warning), and a companion that returns the warning (or one function returning both) feeds the callers. Exact naming is an implementation choice.
4. **Cache.** The state file gets an additional `warning=` line, written with `status=ok`. Old state files without it read as no warning. Changing `zsh-health.bash` makes every cached outcome stale (the helper is watched), so the new check runs once per host after the update.
5. **Callers in `machine`.** The automatic update logs the warning and keeps the update (no revert, no `zsh-unhealthy` event). The manual update shows the warning in its output; the step is not failed and no needs-attention is set because of it. The post-apply health check logs it and stays successful.
6. **Runtime.** A cached outcome needs no trial start at all. A re-check that passes costs two starts instead of one (each with its own timeout); a strict failure costs one start, as today.

## Risks / Trade-offs

- [The dotfiles rely on something from `/etc/zsh/zshrc` (Ubuntu's file runs `compinit` unless `skip_global_compinit` is set and defines key bindings and the `key` array) and print an error only without it] → The strict run would fail although real logins work. `~/.zshenv` already sets `skip_global_compinit=1`; implementation verifies the real config with `+o GLOBAL_RCS` on the desktop and the work VM (tasks) and guards any dependency found.
- [A dotfile error that shows only together with the global files] → It is reported as a warning instead of a failure; exit status and markers still catch hard breakage.
- [The company hook lives in `/etc/zsh/zshenv`] → Then the strict run still fails on it and this change does not help that host; see Assumptions.
- [A company file re-enables `GLOBAL_RCS`] → Only a `$ZDOTDIR` file can do that after the command line unset it; `/etc/zsh/zshenv` runs before and cannot. The dotfiles do not set it.
- [Twice the check time on a re-check, up to twice the timeout on a hang] → Only on re-checks; Ctrl-C still aborts, a timeout stays uncached.

## Migration Plan

Nothing to migrate. The helper change invalidates the cached outcome, so the next eligible bash start runs both trial runs once. A host currently cached as failed because of system output hands over to zsh after that run. Rollback is a dotfiles update that reverts the files; old state files with a `warning=` line are read by the old helper, which ignores unknown keys.

## Assumptions

- The work host (ABTVL421) has no company zsh environment: zsh was installed by the owner and is configured only by the dotfiles (owner, 2026-11-08). Whether the files in `/etc/zsh` there are the unmodified package files, and whether anything there sources `/etc/profile` or `/etc/profile.d`, is not verified; see "Required analysis on the work host".
- The trigger message probably came from the dotfiles, not from a system file. The archived design `2026-11-02-zsh-check-no-lockout` records that "a system login hook" printed `Kerberos token invalid, refreshing...`. That exact line was printed to stderr by `ensure-kerberos-token`, which `home/work/.shell/work/common/environment.sh` ran at every shell start (since `bd7f455`, 2026-02-24) until `7e0588e` (2026-11-02 13:53, change `work-network-autoconnect`) removed the shell-start refresh. If so, the strict check reported a real dotfile output correctly, and this change may have no trigger on that host. Not verified; see "Required analysis on the work host".

## Required analysis on the work host (blocker)

**Blocker:** the open questions, the implementation (tasks 1 and 2) and the decision whether this change is needed at all wait for this analysis. Once the analysis is done and its results are recorded here, remove this blocker (this paragraph, the blocker notes in Open Questions, proposal.md and tasks.md) and update the change to the results.

Points to clarify on ABTVL421 (results go below each point):

1. **Are the global zsh files stock?** Check `/etc/zsh/zshenv`, `zprofile`, `zshrc`, `zlogin` against the package (`dpkg -V zsh-common zsh`, or compare with the files on the desktop) and whether any of them sources `/etc/profile`, `/etc/profile.d` or other company scripts. If they are stock, no system file can print during a zsh start, apart from whatever Ubuntu's `zshrc` itself does.
   - **Result (2026-11-09, ABTVL421 over `ssh osd-vm`, Ubuntu 22.04, and the work laptop LR-C-0042H, Ubuntu 24.04):** not stock. On both hosts `dpkg -V zsh-common zsh` flags only `/etc/zsh/zshrc`. On ABTVL421 it is the package file plus one added line, `[ -f /opt/osd/proxy2/osd-proxy2.sh ] && source /opt/osd/proxy2/osd-proxy2.sh >/dev/null` (checked with `diff` against the downloaded package). On LR-C-0042H the file was replaced by that line alone (88 bytes, the package version is kept as `zshrc.dpkg-dist`). `zshenv`, `zprofile` and `zlogin` do not source `/etc/profile`, `/etc/profile.d` or Kerberos scripts (ABTVL421: read; LR-C-0042H: grep; neither flagged by `dpkg -V`). The hook discards stdout but not stderr, so a company script can print there; it printed nothing in the runs below. This contradicts the first assumption below: the work hosts have a company zsh hook.
2. **Does the Kerberos message still appear, and from where?** `grep -rn 'token invalid' /etc ~/.local/bin ~/.shell` and check that the live checkout contains `7e0588e` (`git -C "$(machine repo)" merge-base --is-ancestor 7e0588e HEAD`). Also check whether the old cron job from `setup-ensure-kerberos-cron` is still installed (`crontab -l`); it does not print into a shell start, but it is a leftover of the same refresh.
   - **Result (2026-11-09):** the line is gone on both hosts: `token invalid` is not found in `/etc`, `~/.local/bin` or `~/.shell`. Both checkouts contain `7e0588e` (ABTVL421: `/mnt/data/home/dci2lr/dotfiles` at `b97cd39`, resolved with `readlink -f ~/.zshrc` because `machine` is not on the PATH of a non-interactive SSH session). `crontab -l` is empty on both, so no leftover cron job.
3. **Current state of the check.** Content of `${XDG_STATE_HOME:-~/.local/state}/dotfiles/zsh-handoff` and the result of `zsh-recheck`. A failure with a reason names the output that matters.
   - **Result (2026-11-09):** `status=ok`, `reason` empty on both hosts (`marker=0` on ABTVL421, `marker=1` on LR-C-0042H). `zsh-recheck` was not run; the starts in point 4 replace it.
4. **Strict versus full start with the real config.** Run both starts as the check does (`DOTFILES_ZSH_CHECK=1`, `TERM` set, stdin `/dev/null`, `setsid -w timeout`): `zsh -l -i +o GLOBAL_RCS -c 'print -r -- "$DOTFILES_ZSH_LOADED $DOTFILES_ZSH_DEFERRED_LOADED"'` and the same without `+o GLOBAL_RCS`; record exit status, markers and stderr of each. Output only in the full start comes from a global file (point 1); output only in the strict start is a dotfile dependency on `/etc/zsh/zshrc` (risk in Risks / Trade-offs).
   - **Result (2026-11-09):** with `TERM=xterm-256color`, both starts exit 0 with markers `1 1` and empty stderr on ABTVL421 and on LR-C-0042H. No global file prints, and the dotfiles do not depend on `/etc/zsh/zshrc` (the strict start passes without it). Starts over non-interactive SSH have `TERM=dumb` and then fail the same way in both modes with dotfile errors (a starship error, `run-compinit` and `compdef` not found), so they are not a global-file effect. On ABTVL421 the old dotfiles started one `ssh-agent` per zsh start (fixed by `ssh-agent-reuse`, not yet pulled there).
5. **Same comparison on the development desktop**, so that a dotfile dependency on Ubuntu's `/etc/zsh/zshrc` shows up independently of the work host.
   - **Result (2026-11-09):** the owner has only two work devices, the laptop LR-C-0042H and the VM ABTVL421, so there is no separate development desktop at work. The laptop (Ubuntu 24.04, `device: desktop` in its host file) serves as the second host in point 4; the strict start passes without Ubuntu's `/etc/zsh/zshrc` content there. A private host was not tested.

**Outcome (2026-11-09):** the first rule applies (no global file printed, the Kerberos line is gone), with one correction: both work hosts have a company hook in `/etc/zsh/zshrc`, so the work VM case in proposal.md is plausible for the future even though it did not occur in these runs. The owner decides to drop the change or keep it as a precaution (task 0.3).

Outcome that decides the next step:
- No global file prints anything on any host and the Kerberos line is gone: the owner decides whether to drop the change or to keep it as a precaution for future hosts; the motivation in proposal.md is then rewritten without the work VM case.
- A global file other than `/etc/zsh/zshenv` prints: the change continues as designed.
- Only `/etc/zsh/zshenv` prints: this design does not help (Non-Goals); the owner decides how to proceed.

## Open Questions

**Blocked:** these questions wait until the analysis in "Required analysis on the work host" is done, because it decides whether the change is needed at all.

Specs and tasks follow the recommendation; a different answer changes the named scenario.

1. **How often is the warning shown at the bash start?** Recommended: only when the check actually runs (then once before the handoff), not on every cached start; the real zsh login prints the same system output itself anyway. Alternative: repeat it on every bash start from the cache. (Scenario "Cached pass with a warning".)
2. **Does a warning appear in `machine attention` or the update prompt segment?** Recommended: no. The user cannot act on company output, and an attention item that never clears would hide real items. It is shown in `machine update` / `machine apply` output and by `zsh-recheck`, and stays in the state file for diagnosis.
3. **Is the full run skipped when the strict run fails?** Recommended: yes. The outcome is already a failure, and skipping it keeps a failing check as fast as today. Alternative: run it anyway to add its stderr to the diagnostic. (Scenario "Strict run fails".)
4. **Does the automatic update record the warning in its event?** Recommended: no new event code; a log line is enough, because the update is kept.
