# Tasks

All work happens in the non-live worktree `.claude/worktrees/xenodochial-ellis-c9a21e` (see proposal, "Where").

## 1. Handoff in the manual update

- [x] 1.1 Split `_update_locked` (`machine_cli/updates.py`) into the part up to `merge_upstream` and `_update_steps(args, steps)` for the remaining steps; behaviour unchanged when `machine_cli/` did not change; verify with the existing update tests in `tests/unit/test_update_and_env.py`
- [x] 1.2 Add `machine_code_changed(previous)` (`git diff --name-only <previous> HEAD -- machine_cli/`) and `run_new_machine_code(args)` that starts `<checkout>/machine_cli/machine update` with the hidden resume options and waits; after the merge, hand over when the code changed; on `OSError` warn and run the steps in-process; when the child exits non-zero without recording needs-attention, record it; verify with tests: handoff with the right command line when `machine_cli/` changed, no handoff otherwise, child failure without state → needs-attention, `OSError` → in-process fallback
- [x] 1.3 In `cmd_update`, run `--resume-from <rev>` without taking the lock and without an `update` event, computing the steps from `<rev>..HEAD`; verify with a test that the resumed run calls the remaining steps (env pull, dotfile apply, tool install) and the system step when `ansible/` changed since `<rev>`

## 2. Handoff in the automatic update

- [x] 2.1 Split `_apply_auto` (`machine_cli/auto_update.py`) into the fast-forward and `_auto_steps(steps)` returning `(failure, code)`; after the fast-forward hand over when `machine_cli/` changed; the child (`--auto --resume-from <rev> --resume-result <file>`) writes the result as JSON; the parent reverts on a reported failure, a non-zero exit, an `OSError` or a missing result (`resume-failed`); verify with tests: success → state "updated" and local stash copy dropped; reported failure → revert with that reason; crash/missing result → revert with `resume-failed`; resumed child writes the result file

- [x] 2.2 Hand over only when the new checkout's `machine_cli/resume-protocol` lists the running code's protocol version; otherwise log it and run the steps in-process (found in code review: a rollback to a CLI without the resume options would otherwise revert or fail); verify with tests for a missing marker and an unknown version, manual and automatic

## 3. CLI

- [x] 3.1 Add hidden `--resume-from` and `--resume-result` options to `update` in `machine_cli/machine`, not shown in `--help`; verify with a test in `tests/unit/test_machine_cli.py` that they parse into the args and do not appear in the help text

## 4. Documentation

- [x] 4.1 Readme update section: one paragraph that steps after the checkout update run with the new `machine` code when `machine_cli/` changed, and that the resume options are internal

## 5. Validation

- [x] 5.1 Run `pytest tests/unit/test_update_and_env.py tests/unit/test_machine_cli.py -q`, then `pytest tests/unit -q` because the update entry point (a shared path) changes; record commands and results here
  - 2026-10-31: `pytest tests/unit/test_update_and_env.py tests/unit/test_machine_cli.py -q` → 163 passed (before the end-to-end test was added); `pytest tests/unit -q` → 839 passed after the black/flake8 fixes. After the code-review fix (2.2): `pytest tests/unit/test_update_and_env.py tests/unit/test_machine_cli.py -q` → 168 passed; `pytest tests/unit -q` → 850 passed; pre-commit on the changed paths passes. The new tests cover the handoff (manual and automatic), the revert in the parent (reported failure, non-zero exit, missing result, cannot start), the in-process fallback, the hidden CLI options, and one end-to-end run that starts the real `machine_cli/machine` of the new revision as the child. The full suite covers the shared update entry point.
- [x] 5.2 Run `pre-commit run --files` on all changed and added paths, including this change directory; record the result
  - 2026-10-31: all hooks pass after black reformatted `updates.py` and the test file and one flake8 E203 in the test helper was fixed
- [x] 5.3 `openspec validate update-runs-new-machine-code --strict`; record the result
  - 2026-10-31: valid
- [x] 5.4 Manual check after merging, on a host one update behind a commit that changes `machine_cli/`: `machine update` logs the handoff and the new step runs in the same update; record the result
  - 2026-10-31, local replay (not a real host; the box stays open): a clone at `b471f87` (the revision of `netmaster` and `oracle`, which already has the handoff) with a scratch `HOME`, updated against `origin/main` `b5d80b3` with the real `machine_cli/machine` and `uv`. `machine update --auto`: "machine_cli changed; running the remaining steps with the new code", the child wrote its result, state `updated`, event `update-auto applied`. `machine update --skip-ansible` without a terminal: the same handoff line, all steps ran in the child, exit 0, state `updated`, one `update applied` event. Caveat: a scratch `HOME` does not isolate dconf/gsettings, so the manual replay re-loaded the GNOME extension settings and the Ddterm font into the laptop session (values identical to the 2026-10-27 dconf backup). Future replays go through `machine testenv`. Starting the update job on `netmaster` was blocked by the permission check; still open: one real host updating from `b471f87` or later over a `machine_cli/` change.
  - 2026-10-31, `netmaster`: a manual `machine update` (19:54:15–19:54:50) from `b471f87` to `7412720`, whose incoming commits change `machine_cli/`, printed "machine_cli changed; running the remaining steps with the new code" (confirmed by the owner from its terminal output) and ended with event `update applied` and state `updated` at `7412720`. The background job started at 19:54:35 found the lock taken and skipped ("another update is running"), as specified.
