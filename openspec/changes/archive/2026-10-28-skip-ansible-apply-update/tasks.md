# Tasks

## 1. CLI and Apply

- [x] 1.1 Add `machine apply --skip-ansible`; verify help and that local/remote
  apply skips bootstrap/Ansible without changing host policy.
- [x] 1.2 Preserve normal apply and `ansible: false` behavior; verify existing
  apply tests pass.

## 2. Update

- [x] 2.1 Add `machine update --skip-ansible`; verify dotfiles/tools still apply
  and Ansible is not invoked.
- [x] 2.2 Verify skipped system changes remain pending and `--system` does not
  override an explicit skip.

## 3. Validation

- [x] 3.1 Run focused machine apply/update unit tests (6 passed).
- [x] 3.2 Run `python3 -m pytest -c tests/pytest.ini tests/unit -q` (433 passed)
  and `pre-commit run --all-files`.
