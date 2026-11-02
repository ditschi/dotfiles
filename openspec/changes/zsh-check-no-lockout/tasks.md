# Tasks

## 0. Owner confirmation

- [x] 0.1 Get the owner's confirmation for design decisions 1–3, which replace the archived "trial keeps the terminal" choice; record the answer in design.md (move it from Open Questions into Decisions) before any code task.

## 1. Detached trial start

- [x] 1.1 Add a PTY regression test to `tests/unit/test_zsh_handoff.py`: interactive bash with the real `handoff.bash`/`zsh-health.bash`, a stub zsh that starts a child reading `/dev/tty` and then sleeps, `DOTFILES_ZSH_CHECK_TIMEOUT=2`; type three commands after the prompt and assert that bash runs all three and the child got nothing. Add `setsid` to the fixture's tool list. Verify that it fails on the current helper (reproduces the lockout).
- [x] 1.2 Change `_zhc_run_checks` in `home/core/.shell/bash/zsh-health.bash` to start the trial as `setsid -w timeout -k 1 <secs> zsh -l -i -c ...` with stdin `/dev/null`, and the documented fallback without `setsid` (design decisions 1, 2 and 4). Verify that the test from 1.1 passes, that a test with a stub child that keeps running after a timeout finds no such process left, and that `pytest tests/unit/test_zsh_handoff.py -q` passes.
- [x] 1.3 Handle Ctrl-C during the trial (design decision 3): end the trial's process group, report "zsh check interrupted", cache nothing, restore the previous `INT` trap. Verify with a PTY test that sends `\x03` during a hanging trial: the prompt appears, a typed command runs, and no state file is written.
- [x] 1.4 Check that `machine`'s zsh checks still work: run `pytest tests/unit/test_update_and_env.py -q -k "zsh or health"` (6 tests) and, from the worktree root, `bash -c '. home/core/.shell/bash/zsh-health.bash; _zhc_run_checks "$(command -v zsh)"' </dev/null`; verify exit 0 and no output.

## 2. Documentation

- [x] 2.1 In `docs/shell.md`, next to `zsh-recheck`, add the rescue login `ssh -t <host> 'bash --noprofile --norc -i'` and say that Ctrl-C skips a running zsh check. Verify that the command works against a reachable host.

## 3. Validation

- [x] 3.1 Run `pytest tests/unit/test_zsh_handoff.py tests/unit/test_update_and_env.py -q`. They cover the helper, the handoff and the `machine` callers. Record the results here.
  - 2026-11-02: 196 passed. Before the fix, the three new tests failed (leftover child alive; bash ran 1 of 3 typed commands; Ctrl-C had no effect for 10 s). `-k "zsh or health"` in `test_update_and_env.py`: 6 passed; `_zhc_run_checks` from the worktree without a terminal: exit 0, no output. Interactive bash skipped the rest of `~/.bashrc` on Ctrl-C until a no-op `INT` trap was added around the check in `dotfiles_zsh_handoff_ok`.
  - Rescue login `ssh -t osd-vm 'bash --noprofile --norc -i'` verified on ABTVL421.
- [x] 3.2 Run `pre-commit run --files home/core/.shell/bash/zsh-health.bash tests/unit/test_zsh_handoff.py docs/shell.md openspec/changes/zsh-check-no-lockout/**` and record the result.
  - 2026-11-02: passed after black reformatted the test file and an SC2086 disable for the intentionally split command prefixes.

## Workflow follow-up

- After merging, on the work VM (ABTVL421): run `zsh-recheck` in an SSH session and confirm the handoff passes; then confirm that an SSH login still accepts input while the check runs, for example with `DOTFILES_ZSH_CHECK_TIMEOUT=5` and a temporary `sleep 30` in `~/.zshrc-local` (removed afterwards). This needs the merged code on the host, so it cannot be done before archiving.
- Before archiving, run `openspec validate --strict --type spec` from the checkout root and treat warnings as blockers.
- Archive inside the worktree, then ask the owner before merging into the live checkout and before removing the worktree.
