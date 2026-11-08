# Proposal

## Why

An env file (`~/.env`, `~/.env.host`, `~/.env.local`) holds secrets. When its permissions are too open, the loader today only prints a warning with a `chmod 600` hint on every shell start. The owner decided (baseline `baseline-env-secrets`, investigation 3) that such a file should be fixed: warn, say that the permissions were fixed, and fix them. On 2026-11-08 the owner decided that both the loader and `machine` do the fixing.

## What Changes

- The env file loader (shell start and `get-password`) changes a file whose group or other bits are set to mode `600`, says so in one line on stderr, and loads it. If the mode cannot be changed, it warns with the `chmod 600` hint as today and still loads the file.
- The check uses the permission bits instead of comparing the mode as a number, so modes like `044` or `604` are caught too; a stricter mode such as `400` is left alone.
- During the zsh health check run (`DOTFILES_ZSH_CHECK=1`) the loader neither changes the mode nor prints anything, so an open env file no longer makes the check fail; the next real shell start fixes it and shows the message.
- `machine env pull`, and through it `machine setup` and `machine update` (including the background job), changes the mode of all three files to `600` when group or other bits are set and logs each change, also when Bitwarden is locked, `bw` is missing or the host has no context.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `env-files`: "Permission warning does not block loading" becomes "Loader fixes too-open env files"; new requirement "machine fixes too-open env files".

## Impact

- Code: `home/core/.shell/common/envfiles.sh` (`dotfiles_load_envfiles`), `machine_cli/env_pull.py` (`cmd_env_pull`).
- Tests: `tests/unit/test_work_net.py` (loader through `get-password`, the existing `test_open_permissions_warn_on_stderr_only`), `tests/unit/test_update_and_env.py` (env pull), `tests/unit/test_zsh_handoff.py` (health check with an open env file).
- Profiles: all contexts and devices; env files exist on every host that uses `machine env pull` or a hand-made `~/.env.local`.
- Where the change is made: worktree `$(machine repo)/.worktrees/env-file-permissions`, because it changes a file every shell start loads and `machine_cli/`.
