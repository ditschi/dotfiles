# Design

## Context

See proposal.md. Current state, verified by reading the code:

- `machine_cli/migration.py` holds `MigrationMixin` (layout detection, rollback script, legacy commit lookup, backup, `preserve_git_host_settings`, stale link clearing, `cmd_migrate`, `cmd_rollback`).
- `cmd_setup` calls the layout check and `preserve_git_host_settings`; `cmd_update` calls `handle_layout_gate` twice; `cmd_status` prints "needs migration".
- `preserve_git_host_settings` returns unless a migration backup exists, so it only serves the migration.
- `install.py` maps to `machine setup|update`. Besides the Readme, CI and `noxfile.py` (compile check) only `home/dot_local/bin/executable_sde` uses it: it checks that the file exists and runs `python3 install.py` for the extended mode, which maps to `machine setup --profile container --yes --no-become` inside Docker.
- `./bootstrap` installs `uv` if missing and runs `machine setup "$@"`, so it covers the same job.

## Goals / Non-Goals

**Goals:**
- Remove the code, tests, CI step and docs that only exist for the old layout migration and for `install.py`.
- Keep `sde --extended` working.

**Non-Goals:**
- Changing `machine update`, `apply` or `setup` behaviour otherwise.
- Removing other subcommands (`commit`, `push`, `inventory`); the report suggests reviewing them separately.

## Decisions

1. **One change, whole migration.** Migration code, the layout gates and the subcommands go together; leaving a gate without the code would break `setup` and `update`.
2. **`sde` uses `./bootstrap`.** The launcher checks for `bootstrap` and runs `"$dotfiles/bootstrap" --profile container --yes --no-become` in extended mode. It behaves like `install.py` did inside Docker (same arguments), without the extra Python wrapper.
3. **Rollback to the old layout ends.** Old commits stay in Git history for anyone who needs them.
4. **Check hosts first.** Removal waits for the owner to confirm that no host still reports "needs migration" and nothing else calls `install.py`.

## Risks

- A host that was never migrated would not be migrated afterwards; `machine setup` would not clear its old root symlinks.
- External scripts calling `install.py` break.

## Investigations (not decided, not in the specs)

None added by this change.
