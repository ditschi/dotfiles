## 1. Health check can fail

- [x] 1.1 Make `health_check_after_apply` return false when the zsh startup health check fails or, with chezmoi installed and its config present, when the config is unreadable or `chezmoi verify` errors; keep telegraf as a warning. Verify: new unit tests for each failing and passing case in `tests/unit/test_host_profiles.py`.
- [x] 1.2 Add a `cmd_update` test with a changed host file and a failing Ansible stub: the old profile is restored and Ansible runs twice; with an unchanged profile it runs once. Verify: `pytest tests/unit/test_host_profiles.py -q`.
- [x] 1.3 Update the Readme apply/update text so the health check and revert description matches the code. Verify: read the Readme section next to the code.

## 2. Update-check job

- [x] 2.1 Test `dotfiles-update-check-job` (fallback path without `machine`) against a local bare repository: marker created when behind, removed when current, kept when the fetch fails, state file written. Verify: new test passes in `pytest tests/unit -q`.
- [x] 2.2 Enable linger best effort in `ensure_update_timer` (skipped without `loginctl` and in Docker; failure only logged) and let `machine setup` reuse it. Verify: unit tests with a stubbed `loginctl` (enables when off, leaves it when on, skipped without it); Readme names the behaviour.

## 3. Safety net coverage

- [x] 3.1 Add or confirm unit tests for the scenarios of the "Automatic update safety net" requirement (revert on zsh failure, no retry of the failed revision, cleared by a manual update). Verify: each scenario maps to a passing test.

## 4. Validation

- [x] 4.1 Run `pre-commit run --all-files` and `pytest tests/unit -q`; fix findings.

## Workflow follow-up

- Archive with `/opsx-archive` after the tasks are done; the delta merges into `openspec/specs/update-flow/spec.md`.
