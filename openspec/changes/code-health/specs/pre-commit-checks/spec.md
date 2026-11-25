# Spec Delta

## MODIFIED Requirements

### Requirement: Pre-commit hooks
`pre-commit` SHALL run the hygiene hooks, `detect-private-key`, `detect-secrets`, `shellcheck`, `shfmt` (4 spaces), `ruff format` and `ruff check` (maximum line length 120, structure rules off), `yamlfmt`, `codespell` and the local hooks `gitconfig-no-host-settings`, `bashrc-no-managed-blocks`, `aihealth-delta`, `aihealth-delta-tests` and `aihealth-suppression-reason`.

#### Scenario: Running all hooks
- **WHEN** a user runs `pre-commit run --all-files`
- **THEN** all of these hooks run

#### Scenario: Delta hooks in CI
- **WHEN** the CI `pre-commit` job runs all hooks
- **THEN** it skips `aihealth-delta` and `aihealth-delta-tests`, because the `code-health` job checks the delta against the merge base
