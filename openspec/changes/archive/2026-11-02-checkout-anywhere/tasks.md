# Tasks

Work only in the worktree `~/dotfiles/.worktrees/checkout-anywhere` (branch `checkout-anywhere`).

## 1. `machine repo`

- [x] 1.1 Add a function in `machine_cli/system.py` that resolves `~/.local/bin/machine` to its checkout (target `<checkout>/machine_cli/machine`, checkout has `.git` and `home/`) and returns `None` with a reason otherwise; verify with unit tests for a valid link, a missing link, a dangling link and a link to a non-checkout.
- [x] 1.2 Add the `repo` command to `machine_cli/machine` (help: "print the path of the live checkout"); print only the path, exit 1 with the reason on stderr; exclude `repo` from `_record_disk_state` and the usage event; verify with unit tests in `tests/unit/test_machine_cli.py` that stdout is exactly the path, that `DOTFILES_REPO` and running a copy from another checkout do not change it, and that no disk state or event file is written.
- [x] 1.3 Check that `machine completion` lists `repo` and that `machine help` shows it; verify with the existing completion/help tests or extend them.
- [x] 1.4 Document `machine repo` in the `Readme.md` command table; verify the table renders and the command works as written.

## 2. Repository detection and status

- [x] 2.1 Extend `detect_repo()` to the order explicit `DOTFILES_REPO` → checkout around the resolved script → checkout from the link → `~/dotfiles`; verify with unit tests for a copy of `machine` outside any checkout and a stale `~/dotfiles`.
- [x] 2.2 Show the checkout path (home as `~`) at the start of the `repo` line in `cmd_status`; verify with the `cmd_status` tests in `tests/unit/test_update_and_env.py` (assert the path appears, also when piped) and update the `machine status` description in `Readme.md`.

## 3. Shell default and background job

- [x] 3.1 Derive the `DOTFILES_REPO` default in `home/core/.shell/common/aliases.sh` from the link (explicit value kept, fallback `$HOME/dotfiles`); verify with a unit test that sources the file in bash and zsh with a fake `HOME`: link into a checkout outside `~/dotfiles` plus a stale `~/dotfiles` → link target; explicit value → kept; no link → `$HOME/dotfiles`; nothing on stderr.
- [x] 3.2 Apply the same rule in `home/core/.local/bin/dotfiles-update-check-job`; verify in `tests/unit/test_update_check_job.py` that without `DOTFILES_REPO` and with the link into a checkout elsewhere the job runs `machine update --auto` (stubbed) instead of exiting early, and that the fallback path still works without the link.
- [x] 3.3 Run `pytest tests/unit/test_zsh_handoff.py -q`, because it covers sourcing `aliases.sh` at shell start; record the result.

## 4. Agent rules

- [x] 4.1 Rewrite "Where to work" in `openspec/config.yaml`, its apply guidance (absolute `git worktree add "$(machine repo)/.worktrees/<change-name>" -b <change-name>`) and the proposal rule to use `machine repo` as defined in design.md "Agent rule"; verify `openspec validate checkout-anywhere` still passes and the YAML parses.
- [x] 4.2 Update the matching bullet in `AGENTS.md` (live checkout = `machine repo`, compare with `git rev-parse --show-toplevel`, absolute worktree path, no live checkout when the command fails); verify by reading it against `openspec/config.yaml` for consistency.

## 5. Integration test

- [x] 5.1 Add a conftest option to start a container without `DOTFILES_REPO` in its environment; verify existing integration tests still pass with the default unchanged.
- [x] 5.2 Add the integration test from design.md (bootstrap from `/dotfiles` with a stale decoy `~/dotfiles`; `machine repo`, interactive zsh/bash `DOTFILES_REPO` and clean stderr, `machine status` path and no warning, update-check job resolving `/dotfiles` offline); verify with `pytest tests/integration -m docker -k <test name>`.

## 6. Validation

- [x] 6.1 Run `pytest tests/unit -q`, because detection is shared by every `machine` command and the shell default affects every shell; record the result.
  - Result: 902 passed. After black formatting and the `removeprefix` change, the focused selection (`test_machine_cli.py`, `test_dotfiles_repo_default.py`, `test_update_check_job.py`, `test_update_and_env.py -k "repo or status or job or default or symlinked"`) passed again (40 passed).
- [x] 6.2 Run `pre-commit run --files <changed paths>` including new files; record the result.
  - Result: passed after black reformatted four files and flake8 E203 in `commands.py` was fixed.
- [x] 6.3 Run the integration tests that start shells or run bootstrap (`tests/integration/test_profile_containers.py` and the new test); record the result and why this selection covers the change.
  - Result: `uvx nox -s docker`: 13 passed (the 11 existing profile tests with the default `DOTFILES_REPO` plus the 2 new tests). The Docker tests need the read-only fix from change `ssh-config-permissions-readonly-checkout`; this branch is based on that branch. The selection covers bootstrap, shell startup in bash and zsh, `machine repo`, `machine status` and the update-check job in a container where the checkout is not `~/dotfiles`.

## Workflow follow-up

- Archive inside the worktree, then ask the owner before merging `checkout-anywhere` into `main` and before removing the worktree.
