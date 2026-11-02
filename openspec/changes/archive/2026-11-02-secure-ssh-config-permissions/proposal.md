## Why

OpenSSH rejected the dotfile-managed SSH config because its checkout target was group-writable. Dotfile apply must enforce SSH-safe permissions so setup and updates do not leave SSH unusable.

## What Changes

- Enforce mode `0600` on the managed SSH config's resolved checkout target during dotfile apply, preserving the existing symlink arrangement.
- Leave unrelated SSH files, keys, ownership and the host's umask unchanged.
- Add focused regression coverage for insecure checkout permissions and repeated apply.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-layout`: dotfile apply guarantees owner-only permissions for the managed SSH config.

## Impact

- Implementation: `machine_cli/dotfiles.py`, in the existing `run_dotfiles_apply` path.
- Tests: extend `tests/unit/test_dotfiles.py`; cover setup/update consumers with the existing focused tests.
- Profiles: all contexts and devices selecting the group that supplies `.ssh/config`.
- Work location: the existing non-live worktree `/home/dci2lr/dotfiles-openspec`, registered separately from the live `/home/dci2lr/dotfiles` checkout. Keep artifacts and implementation together; do not create a nested worktree or modify the live installation.
- No new dependency, command, Ansible change or recursive SSH-directory permission rewrite.

## Assumptions

- Enforce permissions after a successful `mise dot apply`, and only when the installed config resolves to the selected group's config in this checkout. Missing configs, host-local files and foreign symlinks are not permission-repair targets.
- Permission errors should propagate through the existing apply failure handling rather than reporting a successful repair.
- Git checkout under the observed `umask 002` likely produced the original `0664` mode; the historical creation event has not been established.
