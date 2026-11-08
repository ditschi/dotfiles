# Proposal

## Why

The zsh startup health check fails on any error output, wherever it comes from. That catches real dotfile errors: for example, an unguarded `. "$HOME/.cargo/env"` in `~/.zshenv` writes to stderr on hosts without cargo, while the startup markers are still set. But it also fails on output from system startup files in `/etc` that the company owns: on a work VM, a system login hook printed `Kerberos token invalid, refreshing...`, and the check cached zsh as broken. The user cannot fix such output without root, and it must not keep them in the bash fallback. The check should stay strict for the dotfiles and stop treating system output as a failure.

## What Changes

- The health check starts zsh twice. A strict run, `zsh -l -i +o GLOBAL_RCS`, skips the global startup files `/etc/zsh/zprofile`, `/etc/zsh/zshrc` and `/etc/zsh/zlogin` (not `/etc/zsh/zshenv`, which zsh always reads). It fails, as today, on any error output, a non-zero exit, missing startup markers or a timeout.
- A full run, `zsh -l -i` as today, follows a passed strict run. Only its exit status, the markers and the timeout count. Its error output becomes a warning: it is shown where the check ran, but it is not a failure and is not cached as one.
- `machine update`, the automatic update and the post-apply health check treat such a warning as a pass: they show or log it, but do not revert, restore or set needs-attention because of it.
- The cached outcome also records the warning of a pass.
- Unchanged: the cache keys and invalidation, the fresh-host skip, the timeout as an uncached hang guard, Ctrl-C handling and the detached trial start. A cached outcome is reused without any trial start, so the extra run costs time only when the check actually runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shell-handoff`: "Handoff health check" now means the strict run; new requirements cover the full run, the warning for its error output and the cached warning; "Cached result" also stores the warning.
- `update-flow`: a new requirement says that a zsh warning does not fail, revert or restore an update or apply.

## Impact

- Code: `home/core/.shell/bash/zsh-health.bash` (two trial runs, warning output, state file); `machine_cli/auto_update.py` (`zsh_health_failure` and its callers), `machine_cli/updates.py` (manual update), `machine_cli/tools.py` (post-apply health check).
- Tests: `tests/unit/test_zsh_handoff.py` (stub zsh learns `+o GLOBAL_RCS`), `tests/unit/test_update_and_env.py`, `tests/unit/test_host_profiles.py`.
- Docs: `docs/shell.md`.
- Profiles: all hosts with the core dotfile group (work and private; desktop, server and container), since every eligible interactive bash start runs the handoff check; the trigger case is a work VM with company login hooks.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/zsh-check-system-noise` on branch `zsh-check-system-noise`, because the change edits a shell startup helper that the host's shell reads from the live checkout, and `machine`'s update flow.
