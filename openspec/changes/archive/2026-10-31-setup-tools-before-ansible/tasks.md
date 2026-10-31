# Tasks

## 1. Step runner

- [x] 1.1 Add a small helper (for example in `machine_cli/core.py` or a new module) that runs a named step, records ok / failed with reason / skipped because of a failed step it needs, turns `subprocess.CalledProcessError`, `OSError` and `SystemExit` into a failed result, never catches `KeyboardInterrupt`, and prints the summary of failed and skipped steps last; verify with unit tests for each outcome, the dependency skip, the summary text and that Ctrl-C propagates

## 2. Setup order and results

- [x] 2.1 In `machine_cli/commands.py` `cmd_setup`, run the steps through the helper in this order: env pull, dotfile apply, tool install (needs dotfile apply; still guarded by `MACHINE_SKIP_TOOLS`), ready line, Ansible, SSH host key, Tailscale login, update timers (still skipped for `container` and `--skip-dotfiles`); keep `--skip-dotfiles` and skipped Ansible as before; exit non-zero with the summary when a step failed; verify with the tests of 2.3
- [x] 2.2 Print the ready line only when Ansible follows and the dotfile apply and tool install succeeded; verify with the tests of 2.3
- [x] 2.3 Add tests in `tests/unit/test_host_profiles.py` (reusing `_fresh_setup`) for: the call order; env pull failure still applies dotfiles, tools, ready line and Ansible and exits non-zero; dotfile failure skips tools and the ready line but runs Ansible and later steps; Ansible failure still runs SSH key and timers; `--skip-dotfiles`; skipped Ansible without ready line; verify `pytest tests/unit/test_host_profiles.py -q` passes

## 3. Update order and results

- [x] 3.1 In `machine_cli/updates.py` `_update_locked`, after the checkout update, run through the helper: env pull (also on a host that is not set up), dotfile apply, tool install and zsh health check (both need the dotfile apply), then the Ansible apply via `cmd_apply` when due; keep the not-set-up warning and the restore inside `cmd_apply`; verify with the tests of 3.3
- [x] 3.2 On any failed step, write the details to the update failure file, set the state to needs-attention naming the failed steps, record the update event as failed and exit non-zero; on success keep the current state and messages; verify with the tests of 3.3
- [x] 3.3 In `tests/unit/test_update_and_env.py`, change the expected order to `["env", "dotfiles", "tools", "apply"]` and add tests for: env pull failure still applies dotfiles, tools and Ansible and ends needs-attention naming the env pull; dotfile failure skips tools and the zsh check; tool failure still runs Ansible; Ansible failure after an env failure names both; host without `mise` still pulls the env files; verify `pytest tests/unit/test_update_and_env.py -q` passes
- [x] 3.4 Check that `machine update --auto` (`machine_cli/auto_update.py`) is unchanged and its revert tests still pass: `pytest tests/unit -q -k auto`

## 4. Validation

- [x] 4.1 Run `pytest tests/unit -q`, because `cmd_setup` and `cmd_update` are shared entry points whose steps many tests patch and the failure handling changes; record the result
- [x] 4.2 Run `pre-commit run --files` on the changed code, tests and change files, and `openspec validate setup-tools-before-ansible --strict`; record the results

## Workflow follow-up

- Archive the change inside the worktree, then ask the owner before merging the branch into the main clone and before removing the worktree.
