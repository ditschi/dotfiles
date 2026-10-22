# pre-commit-checks Specification

## Purpose
Defines the checks that run on commit and on commit messages.

## Requirements

### Requirement: Pre-commit hooks
`pre-commit` SHALL run the hygiene hooks, `detect-private-key`, `detect-secrets`, `shellcheck`, `shfmt` (4 spaces), `black`, `flake8` (maximum line length 120), `yamlfmt`, `codespell` and the local hook `gitconfig-no-host-settings`.

#### Scenario: Running all hooks
- **WHEN** a user runs `pre-commit run --all-files`
- **THEN** all of these hooks run

### Requirement: shfmt skips .bashrc
`shfmt` SHALL NOT format `.bashrc`, because the work Ansible setup adds blocks that are formatted differently and Ansible would add them again after formatting.

#### Scenario: Formatting shell files
- **WHEN** `shfmt` runs on the repository
- **THEN** `.bashrc` is left unchanged

### Requirement: No co-author trailers
The `commit-msg` hook `no-co-authored-by` SHALL reject commit messages that contain a `Co-authored-by` trailer.

#### Scenario: Commit with a trailer
- **WHEN** a commit message contains `Co-authored-by:`
- **THEN** the commit is rejected
