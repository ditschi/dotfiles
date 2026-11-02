# Proposal

## Why

After a dotfiles update, an SSH login to a work VM stopped accepting input. The bash-to-zsh health check timed out, and a process it had started kept running and read the keystrokes meant for bash. The owner was locked out of SSH and had to use remote desktop. The owner asked for a reliable fix, so that a startup problem in zsh can never lock them out of SSH again.

## What Changes

- The trial zsh start of the handoff health check runs detached from the user's terminal: it cannot read terminal input, and when it ends or times out, nothing it started stays behind.
- The user can interrupt the check with Ctrl-C. The session then stays in bash with the usual one-line diagnostic, and nothing is cached.
- `docs/shell.md` documents a rescue login that skips all startup files, `ssh -t <host> 'bash --noprofile --norc -i'`, next to `zsh-recheck`.
- Unchanged: the timeout stays a generous hang guard (about 60 s) and is still not cached. Error output during the trial still counts as a failure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shell-handoff`: the requirements "Slow or hanging trial start is inconclusive" and "The check never blocks the user" now also require that the trial leaves no process behind, never reads from the user's terminal, and can be interrupted.

## Impact

- Code: `home/core/.shell/bash/zsh-health.bash` (trial start and timeout handling).
- Consumers of the same check: the handoff in `home/core/.shell/bash/handoff.bash`, and `machine`'s post-update and auto-update zsh checks (`machine_cli/auto_update.py`, `machine_cli/tools.py`, `machine_cli/updates.py`), which call `_zhc_run_checks` without a terminal already.
- Tests: `tests/unit/test_zsh_handoff.py` gets a PTY test that reproduces the lockout.
- Docs: `docs/shell.md`.
- Profiles: all hosts with the core dotfile group (work and private; desktop, server and container), since every interactive bash start runs the handoff.
- Dependency: `setsid` from util-linux, which is an essential package on the supported distributions.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/zsh-check-no-lockout` on branch `zsh-check-no-lockout`, because the change edits shell startup files that the host's shell reads directly from the live checkout.
