# Tasks

## 1. Setup reads the repository host config

- [x] 1.1 In `cmd_setup` (`machine_cli/commands.py`), fall back to the repository host config when no applied host config exists: preselect its features when context and device match, and use its `ssh_allow_from` as the current selection. Verify with unit tests in `tests/unit/test_host_profiles.py` for a matching config, a different device and `ssh_allow_from` with `--yes`.
- [x] 1.2 Remove `monitoring` from `machine/hosts/homeserver.yml` and `machine/hosts/netmaster.yml`. Verify with `git diff machine/hosts/`.

## 2. Validation

- [x] 2.1 Run `pre-commit run --all-files` and `pytest tests/unit -q` and verify both pass.

## Workflow follow-up

- Archive the change after review (`/opsx:archive`).
