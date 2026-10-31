# Tasks

All work happens in the worktree `.worktrees/machine-clear-failure-messages`.

## 1. `~/.local/bin` on `PATH`

- [x] 1.1 In `machine_cli/machine`, prepend `~/.local/bin` to `PATH` at start when it is missing; verify with a test in `tests/unit/test_update_and_env.py` that `machine update` with `PATH` lacking `~/.local/bin` and `mise` only in `~/.local/bin` does not report the host as not set up (extend the existing `test_update_warns_when_the_host_is_not_set_up` area)
- [x] 1.2 Document in the Readme (update section) that over `ssh host command` the CLI is called as `~/.local/bin/machine …` and finds its tools itself; verify the text matches the "Run over SSH without a login shell" scenario

## 2. Apply failure names the failing step

- [x] 2.1 In `cmd_apply` (`machine_cli/commands.py`), give Ansible failures and health-check failures separate messages; print the Ansible/sudo hint only for a failed Ansible run; verify with tests in `tests/unit/test_host_profiles.py` (next to `test_apply_reverts_on_health_check_failure`) that a health-check failure says "health check failed" with its reason and no "Ansible", and that an Ansible failure still shows the hint
- [x] 2.2 In `health_check_after_apply` (`machine_cli/tools.py`), when the zsh failure (its first stderr line) is `mise WARN missing: …`, log and run `mise install` once (environment and cwd as in `run_tools_install`) and repeat the check; on a second failure add "run: mise install" to the message; verify with tests: retry passes → apply succeeds and `mise install` ran once; retry fails → apply rolls back and the message names `mise install`; another zsh error → no `mise install`

## 3. Diverged history with conflicting uncommitted changes

- [x] 3.1 Make `rebase_blocker` (`machine_cli/local_work.py`) also report the conflicting uncommitted files, and put them into the plan as the conflicts of a diverged history; verify with a unit test that the plan of a diverged checkout with a conflicting uncommitted change lists that file
- [x] 3.2 In `blocked_reason` (`machine_cli/updates.py`), for this case name the files and the local and incoming commit counts and say "commit, stash or discard them, then run: machine update" instead of `git pull --rebase`; verify with a non-interactive test that the reason is printed last, names the file and does not contain `git pull --rebase`
- [x] 3.3 In `_update_locked`, route this case through `resolve_conflicts` (diff, resolve manually by default, stash) and, after stashing, through `rebase_keeping_local`; `--force` takes the stash; verify with tests: interactive stash choice and `--force` both end with the conflicting change in a named stash entry listed by `machine attention`, the local commits rebased onto the upstream and other uncommitted changes kept; Enter (manual) changes nothing and records needs-attention
- [x] 3.4 Update the Readme passage on diverged history and conflicts to the new behaviour; verify it matches the scenarios

## 4. Validation

- [x] 4.1 Run `pytest tests/unit/test_update_and_env.py tests/unit/test_host_profiles.py -q`, then `pytest tests/unit -q` because the `PATH` change affects every command; record commands and results here
  - Result: `pytest tests/unit/test_update_and_env.py tests/unit/test_host_profiles.py -q` → 173 passed (rerun after the flake8/black fixes); `pytest tests/unit -q` → 743 passed (before those formatting-only fixes). The full suite covers the `PATH` change for every command.
- [x] 4.2 Run `pre-commit run --files` on all changed and added paths, including this change directory; record the result
  - Result: `pre-commit run --files` on all changed and new paths → all hooks pass, after black reformatted `commands.py` and two flake8 findings were fixed (E402 import order in `local_work.py`, E203 in a test).
- [ ] 4.3 Manual check over SSH on `homeserver` after merging: `ssh homeserver '~/.local/bin/machine update --check'` reports no "not set up"; record the result

## Workflow follow-up

- Archive the change inside the worktree, then ask the owner before merging the branch into the main clone and before removing the worktree.
