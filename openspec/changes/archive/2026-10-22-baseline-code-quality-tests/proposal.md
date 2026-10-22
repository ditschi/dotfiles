# Proposal

## Why

Code quality checks, tests and CI are the tenth area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- Quality checks for shell, Python, YAML and secrets run on commit.
- Co-author trailers make commit messages messy; because all commits are AI-assisted, naming AI authorship adds no clarity.
- `.bashrc` is excluded from `shfmt` because the work Ansible setup adds blocks that are not formatted the same way, and formatting them would make Ansible add them again.

## What Changes

- Describe the confirmed behaviour as baseline requirements: the pre-commit hooks, the commit-message hook, the local test commands, the CI jobs, and what is deliberately not in CI.
- Points that are open or planned stay out of the specs and become investigations in design.md: formatting `.bashrc` except for externally managed blocks, removal of the commented-out `protect-files` hook, and which checks must pass before a commit.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `pre-commit-checks`: the hooks that run on commit and on commit messages.
- `tests-and-ci`: the local test commands, the CI jobs and what is left out of CI.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0010-code-quality-tests (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
