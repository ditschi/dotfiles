# Spec Delta

## MODIFIED Requirements

### Requirement: Pre-commit hooks
`pre-commit` SHALL run the hygiene hooks, `detect-private-key`, `detect-secrets`, `shellcheck`, `shfmt` (4 spaces), `ruff format` and `ruff check` (maximum line length 120, structure rules off), `yamlfmt`, `codespell` and the local hooks `gitconfig-no-host-settings`, `bashrc-no-managed-blocks`, `aihealth-delta` and `aihealth-suppression-reason`.

#### Scenario: Running all hooks
- **WHEN** a user runs `pre-commit run --all-files`
- **THEN** all of these hooks run
