# Tasks

Work only in the worktree `~/dotfiles/.worktrees/ssh-config-permissions-readonly-checkout`.

## 1. Read-only checkout

- [x] 1.1 In `run_dotfiles_apply`, skip `chmod` when the target already has mode `0600`, and on `OSError` with `errno.EROFS` log that mode `0600` could not be set (naming the file and its current mode) instead of raising; verify with new unit tests in `tests/unit/test_dotfiles.py` for a read-only error (apply succeeds, message logged, link kept) and an already-`0600` target (no `chmod` call), while `test_ssh_permission_repair_propagates_chmod_failure` still passes.
- [x] 1.2 In `apply_ssh_client`, handle `errno.EROFS` from removing group/other write the same way (log and continue, other errors raise); verify with a unit test in `tests/unit/test_ssh_client.py` for `EROFS` (apply continues and writes the known hosts) and `EPERM` (raises).

## 2. Validation

- [x] 2.1 Run `pytest tests/unit/test_dotfiles.py tests/unit/test_ssh_client.py tests/unit/test_update_and_env.py -q`, because they cover the permission repair and the setup/update callers of dotfile apply; record the result.
  - Result: 228 passed (run with umask 022 and the user-space Git first, as in the archived `secure-ssh-config-permissions` change).
- [x] 2.2 Run the Docker profile tests (`uvx nox -s docker`), because they mount the checkout read-only and failed before this change; record the result.
  - Result: before the fix 11 errors (`Read-only file system: '/dotfiles/home/core/.ssh/config'`); with only 1.1 still failing in `apply_ssh_client` on a `0664` checkout, which led to 1.2; with 1.1 and 1.2: 11 passed.
- [x] 2.3 Run `pre-commit run --files <changed paths>` including new files; record the result.
  - Result: passed after yamlfmt formatted `.openspec.yaml`.

## Workflow follow-up

- Archive inside the worktree, then ask the owner before merging the branch into `main` and before removing the worktree.
