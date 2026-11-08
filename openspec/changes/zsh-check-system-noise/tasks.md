# Tasks

## 1. Health check with strict and full run

- [ ] 1.1 Confirm the open questions in design.md with the owner and adjust the scenarios "Cached pass with a warning" and "Strict run fails" if an answer differs from the recommendation; verify with `openspec validate zsh-check-system-noise --strict`
- [ ] 1.2 Extend the stub zsh in `tests/unit/test_zsh_handoff.py` so that it tells a strict start (`+o GLOBAL_RCS`) from a full start and supports modes that write stderr or fail only in the full run; add tests first for: stderr only in the full run passes with a warning and is cached as a pass; stderr in the strict run fails as today (cargo-like case with markers set); full run exit non-zero, missing markers and timeout fail, timeout uncached; strict failure performs no full run; Ctrl-C during the full run reports "zsh check interrupted"; `zsh-recheck` shows the warning; a cached pass with a warning starts no trial and shows no warning; verify the new tests fail before 1.3
- [ ] 1.3 Implement the two runs in `home/core/.shell/bash/zsh-health.bash` (strict `zsh -l -i +o GLOBAL_RCS -c …`, then full `zsh -l -i -c …`, both with today's environment, `setsid`, timeout and `INT` handling), keep the strict reason text `zsh printed errors on startup: <line>`, print the full-run warning with a fixed prefix on a pass, store `warning=` in the state file, show the warning once in `dotfiles_zsh_handoff_ok` and `zsh-recheck`; verify with `pytest tests/unit/test_zsh_handoff.py -q`
- [ ] 1.4 Update the health check section in `docs/shell.md` (strict and full run, which `/etc/zsh` files each reads, warning instead of failure for system output) and verify the text matches the implemented messages

## 2. machine callers

- [ ] 2.1 Expose the warning to `machine` next to `zsh_health_failure()` in `machine_cli/auto_update.py` (failure stays empty on a pass with a warning) and add a unit test in `tests/unit/test_update_and_env.py` that runs the real helper with a stub zsh whose full run writes stderr; verify with `pytest tests/unit/test_update_and_env.py -q`
- [ ] 2.2 Automatic update: log the warning and keep the update (no revert, no `zsh-unhealthy` event); manual update (`machine_cli/updates.py`): show the warning without `runner.fail` or needs-attention; post-apply health check (`machine_cli/tools.py`): log the warning and stay successful, with `mise install` handling unchanged; add tests in `tests/unit/test_update_and_env.py` and `tests/unit/test_host_profiles.py` for each caller; verify with `pytest tests/unit/test_update_and_env.py tests/unit/test_host_profiles.py tests/unit/test_telegraf.py -q`

## 3. Verification on real hosts

- [ ] 3.1 On the development desktop, run the real config as `DOTFILES_ZSH_CHECK=1 zsh -l -i +o GLOBAL_RCS -c 'print …'` with stdin `/dev/null` and record exit status, markers and stderr; any error output that appears only without the global files is a dotfile dependency to guard before archive
- [ ] 3.2 On the work VM, find which file prints `Kerberos token invalid, refreshing...` (for example `zsh -x -l -i +o GLOBAL_RCS` vs. full start, or grep in `/etc/zsh` and `/etc/profile.d`) and record whether it is `/etc/zsh/zshenv` (assumption in design.md); then run `zsh-recheck` there and verify that the handoff passes, with a warning when the hook prints
- [ ] 3.3 Run `pytest tests/unit -q`, because the change touches the `machine` update flow and the contract of the shared helper; record the result
- [ ] 3.4 Run `pre-commit run --files <changed paths>` (including untracked files) and fix findings
- [ ] 3.5 Run `openspec validate zsh-check-system-noise --strict`
- [ ] 3.6 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change touches the `machine` update flow and two capabilities; fix findings before archive

## Workflow follow-up

- Archive the change with spec sync (`/opsx-archive`) in the worktree after the review.
