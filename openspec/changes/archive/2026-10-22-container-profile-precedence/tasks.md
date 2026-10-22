# Tasks

## 1. Profile detection

- [x] 1.1 Change `default_profile()` and the saved-profile reader in `home/dot_local/lib/machine_cli/profile.py` to follow the new order; verify with a unit test that a saved host profile is ignored in Docker and that `MACHINE_PROFILE_OVERRIDE` wins.
- [x] 1.2 Add the Docker check, the override and the `container` rule for `WORK_SETUP` to `home/dot_zsh/machine-profile.sh`; verify with a shell test in zsh and bash (and in `tests/unit`, using `MACHINE_IN_DOCKER=1`).
- [x] 1.3 Keep the company user ID regex in one place (shell script or a shared helper); verify `profile.py` and the shell script give the same answer for sample names.

## 2. Tests

- [x] 2.1 Pass `MACHINE_PROFILE_OVERRIDE` into the test containers in `tests/integration/conftest.py`; verify `test_shells_start_cleanly` and `test_profile_dotfiles` still expect each profile.
- [x] 2.2 Update `test_dev_container_with_work_user_starts_cleanly` to expect `container|` (empty `WORK_SETUP`); verify it in Docker (not run here: the image build fails on a certificate error).

## 3. Documentation and validation

- [x] 3.1 Update `Readme.md` where it describes profile detection; verify no old order remains.
- [x] 3.2 Run `uvx nox -s tests` and `pre-commit run --all-files`; verify both pass.
- [x] 3.3 Run `openspec validate container-profile-precedence --strict`; verify it passes.

## Workflow follow-up

- Archive the change after implementation (`/opsx-archive`).
