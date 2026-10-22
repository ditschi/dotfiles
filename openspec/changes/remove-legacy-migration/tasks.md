# Tasks

## 0. Gate

- [ ] 0.1 Check `machine status` on every host: "needs migration" is `False`, and no host, cron job or note calls `install.py`; verify with the owner before removing code.

## 1. Code

- [ ] 1.1 Delete `home/dot_local/lib/machine_cli/migration.py` and its `MigrationMixin` entry in `machine.py`; verify the module imports.
- [ ] 1.2 Remove the layout check and `preserve_git_host_settings` call from `cmd_setup`, both `handle_layout_gate` blocks from `cmd_update`, and the "needs migration" line from `cmd_status` in `commands.py`; verify `machine setup --help` and `machine update` still work.
- [ ] 1.3 Remove the `migrate` and `rollback` subcommands, `--rollback-ref` and `_setup_or_migrate` in `executable_machine`; verify `machine --help` lists neither.
- [ ] 1.4 Change `executable_sde` to check for and run `./bootstrap --profile container --yes --no-become` in extended mode; verify with the sde tests in `tests/unit/test_machine_cli.py`.
- [ ] 1.5 Delete `install.py` and remove it from the `machine commit` file list.

## 2. Tests and CI

- [ ] 2.1 Delete `tests/integration/test_migrate.py` and the `migrate` service in `tests/compose.yaml`; remove the "Migration from old root layout" step and `install.py` compile checks from `.github/workflows/verify.yml`, and the `install.py` entries and migration lab hint from `noxfile.py`.
- [ ] 2.2 Remove the migration unit tests (`test_needs_layout_migration_detects_old_root_symlink`, `test_write_rollback_script`, `test_migration_*`, `test_git_host_settings_*`), the `handle_layout_gate` monkeypatch in `tests/unit/test_gitconfig.py`, and the `migrate`/`rollback` help assertions; update the sde test fixture that writes `install.py`.

## 3. Documentation and validation

- [ ] 3.1 Remove the Readme sections "Migration", "Revert" and "Legacy commands", the `migrate`/`rollback` table rows and the `migration` module row; verify no link or mention of `install.py` or `machine migrate` remains.
- [ ] 3.2 Run `uvx nox -s tests` and `pre-commit run --all-files`; verify both pass.
- [ ] 3.3 Run `openspec validate remove-legacy-migration --strict`; verify it passes.

## Workflow follow-up

- Archive the change after implementation (`/opsx-archive`).
