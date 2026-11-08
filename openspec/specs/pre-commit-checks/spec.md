# pre-commit-checks Specification

## Purpose
Defines the checks that run on commit and on commit messages.

## Requirements

### Requirement: Pre-commit hooks
`pre-commit` SHALL run the hygiene hooks, `detect-private-key`, `detect-secrets`, `shellcheck`, `shfmt` (4 spaces), `black`, `flake8` (maximum line length 120), `yamlfmt`, `codespell` and the local hooks `gitconfig-no-host-settings` and `bashrc-no-managed-blocks`.

#### Scenario: Running all hooks
- **WHEN** a user runs `pre-commit run --all-files`
- **THEN** all of these hooks run

### Requirement: shfmt checks .bashrc without rewriting it
`shfmt` SHALL check `home/core/.bashrc` and fail when its formatting differs, but SHALL NOT rewrite it, because the work Ansible setup adds blocks to `~/.bashrc` that are formatted differently and Ansible would add them again after formatting. The local hook `bashrc-no-managed-blocks` SHALL fail when `home/core/.bashrc` contains an externally managed block (`# BEGIN ... MANAGED BLOCK`), so the block is moved to `~/.bashrc-local` before it is committed.

#### Scenario: Formatting shell files
- **WHEN** `shfmt` runs on the repository
- **THEN** `.bashrc` is left unchanged

#### Scenario: Unformatted .bashrc
- **WHEN** `shfmt` runs on a `home/core/.bashrc` whose formatting differs
- **THEN** the hook fails and shows the difference
- **AND** `home/core/.bashrc` is left unchanged

#### Scenario: Managed block in .bashrc
- **WHEN** the hooks run on a `home/core/.bashrc` that contains `# BEGIN ANSIBLE MANAGED BLOCK`
- **THEN** `bashrc-no-managed-blocks` fails and its message names `machine update`
- **AND** `home/core/.bashrc` is left unchanged

### Requirement: No co-author trailers
The `commit-msg` hook `no-co-authored-by` SHALL reject commit messages that contain a `Co-authored-by` trailer.

#### Scenario: Commit with a trailer
- **WHEN** a commit message contains `Co-authored-by:`
- **THEN** the commit is rejected
