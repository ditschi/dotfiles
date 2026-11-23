# Spec Delta

## Purpose

Measures the health of the repository's code on a scale from 1 to 10 per part (Python CLI, tests, shell scripts), modelled on CodeScene Code Health with free tools only, and keeps it from getting worse through a gate in pre-commit and CI.

## ADDED Requirements

### Requirement: Scored files
The checker SHALL score the Python files and shell scripts (sh, bash, zsh) matched by the scope globs in `code-health.toml` among the files git does not ignore. A shell file without any function and without `if`, `for`, `while`, `until` or `case` SHALL count as configuration: it is listed with score 10 and weight 0. YAML outside the Ansible roles and playbooks SHALL NOT be scored.

#### Scenario: Shell file with only aliases and exports
- **WHEN** a scored shell file contains only aliases, exports and option settings
- **THEN** it does not change its part score

#### Scenario: Ansible variables
- **WHEN** the checker runs on the repository
- **THEN** inventory and `group_vars` files are not scored

### Requirement: Ansible smells
For the `ansible` part, the checker SHALL report task files with more tasks than the threshold, `when` conditions with two or more `and`/`or` operators, `block` nesting from the threshold, templates with more Jinja control tags than the threshold, and tasks that repeat another task of the same role.

#### Scenario: Long task file
- **WHEN** a role's task file holds more tasks than the configured limit
- **THEN** a `large-file` smell is reported for that file

### Requirement: File score
Each scored file SHALL start at 10.0; each smell SHALL deduct `min(max, base + step × (value − first firing value))` with `base`, `step` and `max` from the rule's entry in `code-health.toml`. The file score SHALL NOT drop below 1.0. A file that cannot be parsed SHALL score 1.0 and report the parse error.

#### Scenario: File without smells
- **WHEN** a file has no smells
- **THEN** its score is 10.0

#### Scenario: Many smells
- **WHEN** the deductions of a file add up to more than 9
- **THEN** its score is 1.0

### Requirement: Part scores
Each scored file SHALL belong to exactly one part defined by globs in `code-health.toml`: `python-cli` (`machine_cli` and the other Python programs), `python-tests` (`tests/`), `shell` (shell scripts with logic) and `ansible` (task files and templates of roles and playbooks). Each part score SHALL be the mean of its file scores weighted by lines of code without blank lines, comments and docstrings. The target of 9.5 SHALL apply to each part.

#### Scenario: Two files of one part
- **WHEN** a 100-line file scores 10.0 and a 300-line file of the same part scores 6.0
- **THEN** the part score is 7.0
### Requirement: Overall score
The output SHALL show an overall score as the mean of all file scores weighted by lines of code, for information only, and SHALL name the file with the lowest score. The gate SHALL NOT use the overall score.

#### Scenario: Strong Python, weak shell
- **WHEN** the Python parts score 9.8 and the shell part scores 8.0
- **THEN** the overall score is shown, and the shell part is reported below its target
### Requirement: Rules per part
Each part SHALL have its own set of rules and thresholds in `code-health.toml`. A rule that is not configured for a part SHALL NOT be reported for that part's files.

#### Scenario: Fixture arguments in a test
- **WHEN** a test function takes six pytest fixtures
- **THEN** no `excess-arguments` smell is reported, because the rule is not configured for `python-tests`

### Requirement: Function smells
The checker SHALL report per function, where the part configures the rule: complex method (cyclomatic complexity), large method (lines of code), brain method (complex and large at once), excess arguments (constructors: constructor over-injection), deep nested complexity, bumpy road (several separate nested blocks), complex conditional (`and`/`or` operators in one branch condition) and cognitive complexity.

#### Scenario: Complex function
- **WHEN** a Python function has a cyclomatic complexity of 10 and the threshold is 9
- **THEN** a `complex-method` smell is reported with the function's name and line

#### Scenario: Shell function nesting
- **WHEN** a shell function nests `if`, `for`, `while` or `case` as deep as the shell part's nesting limit
- **THEN** a `nested-complexity` smell is reported for that function
### Requirement: Module smells
The checker SHALL report per file: large file, overall code complexity (mean cyclomatic complexity), many functions, primitive obsession (share of arguments typed as built-in primitives), brain class (large file with many functions and a brain method), low cohesion of a class (LCOM4) and code duplication between similar functions of the same file.

#### Scenario: Copied function
- **WHEN** two functions of at least 10 lines in one file are at least 75 % similar
- **THEN** a `code-duplication` smell is reported for the second one, naming the first

### Requirement: Test smells
In files matched by the `tests` globs, the checker SHALL report large assertion blocks (files with several blocks of consecutive assertions above the configured size) and duplicated assertion blocks (the same consecutive assertions in more than one test).

#### Scenario: Repeated assertions
- **WHEN** two test functions contain the same two consecutive `assert` statements
- **THEN** a `duplicated-assertion-blocks` smell is reported for the second

### Requirement: Versioned configuration
Scope, thresholds, deductions and the gate settings SHALL be read from `code-health.toml` in the repository root. Each threshold SHALL state in a comment whether it is a published CodeScene default or an own assumption.

#### Scenario: Changing a threshold
- **WHEN** a threshold in `code-health.toml` is changed and committed
- **THEN** the next run uses it without code changes

### Requirement: Command and output
`uvx nox -s code-health` and `python3 -m code_health` SHALL print a table of the files with smells (score, lines, file) and per smell its line, rule, deduction and detail, followed by the part scores, the overall score and the worst file. `--all` SHALL list files without smells too.

#### Scenario: Default run
- **WHEN** a user runs `python3 -m code_health`
- **THEN** every file with smells is listed, lowest score first, followed by the part scores

### Requirement: JSON output
With `--json` the command SHALL print one JSON object with the part scores, the overall score, the worst file and per file its path, language, lines, score, smells (rule, line, target, detail, deduction) and errors; with `--gate` it SHALL also contain the gate result.

#### Scenario: Agent reads the result
- **WHEN** an agent runs `python3 -m code_health --json --changed`
- **THEN** it gets the smells of the changed files as JSON

### Requirement: Changed files only
`--changed [BASE]` SHALL limit the listed files to scored files changed since `BASE` (committed, staged, unstaged or untracked); without `BASE` it SHALL use the merge base with `origin/main`. Explicit paths SHALL limit the listing to those files.

#### Scenario: Branch with one changed module
- **WHEN** a branch changed one scored file and `--changed` is given
- **THEN** only that file is listed

### Requirement: Gate for changed files
With `--gate`, the command SHALL fail when a changed file scores below the minimum file score (9.5) or below its score at the base revision, or reports an error. A file listed in the baseline SHALL instead need at least its baseline score.

#### Scenario: New smell in a healthy file
- **WHEN** a commit adds a smell to a file that scored 10.0
- **THEN** the gate fails and names the file and both scores

#### Scenario: Baseline file improves
- **WHEN** a file with baseline score 4.0 now scores 5.0
- **THEN** the gate passes and suggests tightening the baseline

### Requirement: Part scores do not fall
With `--gate`, the command SHALL fail when a part score is below that part's value in the baseline, or below the minimum file score when the baseline has no value for the part.

#### Scenario: Shell scripts get worse
- **WHEN** a change lowers the shell part score below its baseline value while the Python parts improve
- **THEN** the gate fails and names the shell part
### Requirement: Ratchet baseline
`--update-baseline` SHALL write `code-health-baseline.json` with each part score and the score of each file below the minimum file score. When the file exists, entries SHALL only rise or be removed: a file that got worse keeps its old entry, a new file is not added, and part scores only rise.

#### Scenario: Tightening
- **WHEN** a baseline file improved from 4.0 to 9.6 and `--update-baseline` runs
- **THEN** its entry is removed from the baseline

### Requirement: Pre-commit and CI gate
A local pre-commit hook `code-health` SHALL run the gate on the staged scored files against `HEAD`, and the CI workflow SHALL run the gate on the files changed against the merge base with `main`.

#### Scenario: Commit that worsens a file
- **WHEN** a commit lowers the score of a scored file
- **THEN** the `code-health` hook fails the commit

### Requirement: Inline suppressions
A smell SHALL be suppressed only by a comment `code-health: ignore[<rule>[, <rule>]] <reason>` on the smell's line or the line above it. A suppression without a reason, or one that matches no smell, SHALL be reported as an error, which fails the gate.

#### Scenario: Suppression without reason
- **WHEN** a function carries `# code-health: ignore[complex-method]` without a reason
- **THEN** the file reports an error and the gate fails
