# Spec Delta

## Purpose

Measures the health of the repository's Python and shell code on a scale from 1 to 10 per component with ai-health, modelled on CodeScene Code Health, and keeps it from getting worse through a gate in pre-commit and CI.

## ADDED Requirements

### Requirement: Pinned tool
Code health SHALL be measured with ai-health, pinned to one commit in exactly one place, the wrapper `scripts/aihealth`. Every hook, CI step and nox session SHALL call ai-health through that wrapper.

#### Scenario: Updating ai-health
- **WHEN** the pinned commit is changed in `scripts/aihealth`
- **THEN** the hook, CI and nox use the new version without further edits

### Requirement: Components
The code SHALL be scored in three components: `python-cli` (Python files outside `tests/` and `openspec/`), `python-tests` (Python files under `tests/`) and `shell` (shell files ai-health detects outside `tests/` and `openspec/`). Each component score SHALL be the mean of its file scores weighted by lines of code.

#### Scenario: Report per component
- **WHEN** a user runs `uvx nox -s code-health`
- **THEN** the output shows one score for each of `python-cli`, `python-tests` and `shell`

### Requirement: Not scored
Ansible files SHALL NOT get a score; ansible-lint SHALL remain their gate. Python scripts without a file extension SHALL be listed in `docs/code-health.md` as not scored while ai-health cannot detect them.

#### Scenario: Script without extension
- **WHEN** ai-health scans the repository
- **THEN** `machine_cli/machine` is not scored and the docs name this gap

### Requirement: Strict profile
The thresholds, score parameters and delta tolerance SHALL be set in `.aihealth.toml` (profile "strict": CodeScene thresholds, file size 600 lines, primitive obsession 30 %, decay 8, density 100 000 lines, tolerance 0). `.aihealth-tests.toml` SHALL repeat these values unchanged and set the weights of excess arguments, primitive obsession and low cohesion to 0.

#### Scenario: Diverging test profile
- **WHEN** `.aihealth-tests.toml` sets a threshold that differs from `.aihealth.toml`
- **THEN** the unit tests fail

#### Scenario: Fixture arguments
- **WHEN** a test function takes six pytest fixtures
- **THEN** no excess-arguments finding is reported for it

### Requirement: Explicit configuration
Every ai-health call SHALL pass the configuration of its component with `--config`, so that no call falls back to the defaults.

#### Scenario: Scanning the tests directory
- **WHEN** the tests component is scanned
- **THEN** ai-health reads `.aihealth-tests.toml` from the repository root

### Requirement: Changed files for agents
`scripts/aihealth delta` SHALL compare the changed files of the working tree with `HEAD` per component and exit with 1 when a file got worse or a new file has a finding; `--format json` SHALL give the same result as JSON.

#### Scenario: Agent checks its change
- **WHEN** an agent runs `scripts/aihealth delta --format json` after editing a module
- **THEN** it gets the new and worsened findings of the changed files

### Requirement: Pre-commit gate
A pre-commit hook SHALL run `delta --staged` for each component and fail when a staged file got worse or a new file has a finding.

#### Scenario: Commit that adds a finding
- **WHEN** a commit adds a complex function to a file without findings
- **THEN** the hook fails and names the file and the finding

### Requirement: CI gate
The CI SHALL run `delta` per component between the merge base with `main` and `HEAD`, and SHALL fail when the score of a component at `HEAD` is lower than at the merge base by more than 0.01. The CI SHALL cache the tree-sitter grammars.

#### Scenario: Branch behind main
- **WHEN** a branch is behind `main` and changes one file without making it worse
- **THEN** the gate passes, because it compares against the merge base

#### Scenario: Component gets worse
- **WHEN** a pull request lowers the `shell` component score
- **THEN** the CI gate fails and names the component

### Requirement: Suppressions with reason
A finding SHALL be suppressed only file-wide with `# aihealth: disable=<smell>[, <smell>] -- <reason>`; a pre-commit hook SHALL reject a suppression without ` -- ` and a reason of at least ten characters.

#### Scenario: Suppression without reason
- **WHEN** a file contains `# aihealth: disable=complex_method`
- **THEN** the hook fails

### Requirement: Target score
The target for every file and component SHALL be 10 (no finding); 9.5 SHALL be the minimum on the way there.

#### Scenario: Reviewing a component
- **WHEN** a component scores 9.6
- **THEN** it meets the minimum, and its remaining findings are still to be fixed
