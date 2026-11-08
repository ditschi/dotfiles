# Tasks

Work only in the worktree `$(machine repo)/.worktrees/env-file-permissions`.

## 1. Loader

- [ ] 1.1 In `tests/unit/test_work_net.py`, change `test_open_permissions_warn_on_stderr_only` to expect mode `600` afterwards and a stderr line naming `.env` and `644`, and add cases for `044` (fixed), `400` (unchanged, no output) and a failing `chmod` (stub `chmod` on `PATH` that exits 1: warning with `chmod 600`, password still printed); verify they fail.
- [ ] 1.2 In `home/core/.shell/common/envfiles.sh`, replace the numeric `-gt 600` check with a group/other bit check, run `chmod 600`, print the fix line or, on failure, today's warning, and skip the whole step when `DOTFILES_ZSH_CHECK` is set; verify `pytest tests/unit/test_work_net.py -q` passes, including `test_shell_loader_still_exports_env_files` for bash and zsh.
- [ ] 1.3 In `tests/unit/test_zsh_handoff.py`, add a test that the health check passes with a `~/.env` of mode `644` and leaves the mode unchanged; verify it passes.

## 2. machine

- [ ] 2.1 In `tests/unit/test_update_and_env.py`, add tests that `cmd_env_pull` changes `~/.env.local` from `664` to `600` and logs the file and old mode when Bitwarden is locked and when there is no context, and logs nothing when all files are `600`; verify they fail.
- [ ] 2.2 In `machine_cli/env_pull.py`, fix the three env files at the start of `cmd_env_pull` as outlined in design.md; verify `pytest tests/unit/test_update_and_env.py -q` passes.

## 3. Documentation

- [ ] 3.1 In `docs/secrets.md`, below the env file table (around line 64), add that a too-open env file is changed to `600` by the shell start and by `machine env pull`/`setup`/`update`, and that the health check run leaves it alone; the docs do not mention the old warning today.

## 4. Validation

- [ ] 4.1 Run `pytest tests/unit/test_work_net.py tests/unit/test_zsh_handoff.py tests/unit/test_update_and_env.py tests/unit/test_machine_cli.py -q`; they cover the loader in both shells, `get-password`, the health check and the setup/update flows that call env pull. Record the results here.
- [ ] 4.2 Run `pre-commit run --files <changed paths>` (including `openspec/changes/env-file-permissions/**`) and record the result.
- [ ] 4.3 Run `openspec validate env-file-permissions --strict` and record the result.

## Workflow follow-up

- Archive inside the worktree, then ask the owner before merging into `main` and removing the worktree.
