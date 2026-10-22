# Proposal

## Why

All hosts are already on the chezmoi layout, so the code that migrated hosts from the old root layout (and rolled back) is dead weight on the main setup path: `machine setup` and `machine update` still check for old root symlinks, and about 480 lines of migration code, two subcommands, a Docker test and README sections exist only for it. `install.py` is a thin wrapper that nothing in the repository needs except the `sde --extended` launcher.

## What Changes

- Remove `machine_cli/migration.py` (migration, rollback script, legacy commit lookup, stale link clearing) and the `migrate` and `rollback` subcommands with `--rollback-ref`.
- Remove the layout checks from `machine setup` and `machine update`, and the "needs migration" line from `machine status`.
- Remove `preserve_git_host_settings` too: `machine setup` calls it, but it returns immediately unless a migration backup exists, so it only serves the migration.
- Remove `install.py`. The `sde --extended` launcher calls `./bootstrap --profile container --yes --no-become` instead.
- Remove the Docker migration test and lab (`tests/integration/test_migrate.py`, the `migrate` service in `tests/compose.yaml`, the CI step), the migration unit tests, and the README sections "Migration", "Revert" and "Legacy commands".
- Remove `install.py` from `machine commit`'s file list, `noxfile.py` and CI compile checks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `update-flow`: no layout migration in setup or update.
- `repo-layout`: `./bootstrap` is the single entry point; there is no `install.py`.

## Open Questions

- Does any host, cron job or note still call `install.py` or have old root symlinks? Check `machine status` ("needs migration") on every host before this is applied. The earlier report suggested waiting until after 2026-10-28.
- The Readme "Revert" text describes going back to the old layout with the old commit's `install.py`. Removing it ends the documented way back; the old commits stay in Git history.

## Impact

- Code: `home/dot_local/lib/machine_cli/{migration,commands,machine}.py`, `home/dot_local/bin/executable_machine`, `home/dot_local/bin/executable_sde`, `install.py`.
- Tests and CI: `tests/integration/test_migrate.py`, `tests/compose.yaml`, `tests/unit/test_machine_cli.py`, `tests/unit/test_host_profiles.py`, `tests/unit/test_gitconfig.py`, `.github/workflows/verify.yml`, `noxfile.py`.
- Docs: `Readme.md`.
- Reports: `openspec/investigations/architecture-and-profiles.md` items A4, A5.
