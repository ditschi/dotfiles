# Code health

A score from 1 to 10 per file and per part of the repository, modelled on [CodeScene Code Health](https://codescene.io/docs/guides/technical/code-health.html) but computed with our own checker (`code_health/`, standard library plus PyYAML). Target: every part at 9.5 or more, ideally 10. Agents develop against it; pre-commit and CI keep it from getting worse.

## Commands

```bash
python3 -m code_health                     # table: files with smells, part scores, worst file
python3 -m code_health --changed           # only files changed since the merge base with origin/main
python3 -m code_health --changed HEAD      # only uncommitted changes
python3 -m code_health --json --changed    # the same as JSON, for agents
python3 -m code_health --all machine_cli/updates.py   # one file, also when it has no smells
python3 -m code_health --gate --changed    # what CI checks; exit code 1 on failure
python3 -m code_health --update-baseline   # tighten code-health-baseline.json after an improvement
uvx nox -s code-health -- --changed        # the same through nox
```

A full run takes about 4 seconds. The table lists per smell its line, rule, deduction and detail:

```text
 score    loc  file
  8.35    120  machine_cli/machine.py
               L330   complex-method               -0.5   _scratch: cyclomatic complexity 10
```

## Parts

| Part | Files | Measured like |
| --- | --- | --- |
| `python-cli` | `machine_cli/`, `code_health/`, `noxfile.py`, Python programs under `home/` and `ansible/roles/*/files/` | an application: all function, module and class rules |
| `python-tests` | `tests/` | tests: size, complexity, duplication, assertion blocks; no argument, primitive or cohesion rules (pytest fixtures arrive as arguments) |
| `shell` | sh, bash and zsh files with logic under `home/`, `machine/`, `ansible/roles/*/files/`, `bootstrap` | scripts: complexity, size, nesting, bumpy road, conditionals, duplication, with lower size and nesting limits |
| `ansible` | playbooks, task files, handlers and templates | tasks per file, complex `when`, `block` nesting, Jinja control tags, duplicated tasks |

A shell file without functions and without `if`/`for`/`while`/`until`/`case` (aliases, exports, options) and a template without Jinja control tags count as configuration: score 10, weight 0. Inventory and `group_vars` are not scored. Correctness stays with shellcheck and ansible-lint.

## Score

Every file starts at 10.0. Each smell deducts `min(max, base + step × (value − first firing value))`, and the score never drops below 1.0. A part's score is the mean of its file scores weighted by lines of code (without blank lines, comments and docstrings). The overall score over all parts is shown for information only; the gate uses the part scores.

Thresholds and deductions are in [code-health.toml](../code-health.toml); each value says whether it is a published CodeScene default (Python, `default-rules.zip`, May 2025) or an own assumption.

| Rule | Fires when | Origin |
| --- | --- | --- |
| `complex-method` | cyclomatic complexity > 9 (Ansible templates: > 10 Jinja `if`/`elif`/`for`) | CodeScene (templates: assumption) |
| `large-method` | > 70 lines (shell: > 40) | CodeScene (shell: assumption) |
| `brain-method` | complex-method and large-method at once | assumption |
| `excess-arguments` | > 4 arguments, `self`/`cls` not counted | CodeScene |
| `constructor-over-injection` | `__init__` with > 5 arguments | CodeScene |
| `nested-complexity` | nesting of `if`/`for`/`while`/`try`/`match` ≥ 4 (shell, Ansible `block`: ≥ 3) | CodeScene (shell, Ansible: assumption) |
| `bumpy-road` | ≥ 2 separate top-level chunks nested ≥ 2 deep | CodeScene |
| `complex-conditional` | ≥ 2 `and`/`or` operators in one branch condition (shell `&&`, `\|\|`, `-a`, `-o`; Ansible list items count as `and`) | CodeScene, read as operators |
| `cognitive-complexity` | > 15 (SonarSource) | assumption |
| `code-duplication` | two functions of ≥ 10 lines and ≥ 40 tokens, ≥ 75 % similar (Ansible: tasks ≥ 95 % similar) | CodeScene (tokens, Ansible: assumption) |
| `large-file` | > 600 lines (shell: > 300; Ansible: > 40 tasks) | CodeScene (shell, Ansible: assumption) |
| `overall-code-complexity` | mean cyclomatic complexity of the functions > 4 | CodeScene |
| `many-functions` | > 40 functions and methods | assumption |
| `primitive-obsession` | > 50 % of the annotated arguments are `str`/`int`/`float`/`bool`/`bytes` (from 10 annotated arguments) | CodeScene 30 %, raised to 50 % and annotated only (owner decision) |
| `brain-class` | large file with ≥ 20 functions and a brain method | assumption |
| `low-cohesion` | LCOM4 ≥ 2 in a class with ≥ 4 methods | assumption |
| `large-assertion-blocks` | ≥ 4 blocks of ≥ 4 consecutive asserts in a test file | CodeScene |
| `duplicated-assertion-blocks` | the same ≥ 2 consecutive asserts in another test | assumption |

## Gate, baseline and suppressions

The pre-commit hook `code-health` and the CI job `unit` run `--gate`. It fails when

- a changed file scores below 9.5, or below its entry in the baseline when it has one,
- a changed file scores lower than at the base revision (`HEAD` in pre-commit, the merge base with `main` in CI),
- a part score is below its baseline value (or below 9.5 without one),
- a changed file has an error: it cannot be parsed, or a suppression lacks a reason or matches no smell.

`code-health-baseline.json` is the ratchet while a part is below 9.5: it holds each part's score and each file below 9.5. `--update-baseline` only tightens it: entries rise or disappear, new files are never added. The gate prints a hint when the baseline can be tightened.

Fix smells instead of suppressing them. When code cannot reasonably be shaped otherwise, suppress one smell with a comment on its line or the line above, naming the rule and the reason:

```python
# code-health: ignore[complex-method] mirrors the 12 states of the protocol table
def transition(state, event):
```

## Steckbrief Code Health

Profile for comparing this approach with the other repositories; the headings are fixed.

### 1. Messumfang

Four parts, each with its own score and its own target of 9.5 (see [Parts](#parts)): `python-cli` (measured like an application), `python-tests`, `shell`, `ansible`. Python counts completely. Shell and zsh files count only when they contain a function or control structures; plain rc files with aliases, exports and options would otherwise lift the shell score with many lines at 10. For Ansible, playbooks, task files, handlers and templates with Jinja logic count, but not inventory and `group_vars` (data only). The overall score across the parts (weighted by lines) is information only, because the large Python share (29 000 of 33 000 lines) would hide shell and Ansible.

### 2. Tools und Versionen, je Sprache

- Python: own checker on the standard library's `ast` and `tokenize` (Python 3.11 or newer). Cross-checked against radon 6.0.1 (cyclomatic complexity equal for 533 of 537 functions) and complexipy 9.0.0 (cognitive complexity equal for 526 of 537; complexipy adds nested functions to the outer one). Both are references, not dependencies.
- Shell: own line-based parser that relies on the layout shfmt enforces; no free tool measures the complexity of shell code. Correctness: shellcheck 0.11 (pre-commit).
- Ansible: PyYAML 6 (`yaml.compose`, for line numbers). Correctness: ansible-lint (CI).
- Checked and not used: lizard 1.26.1 (no shell, no nesting or bumpy-road data), ruff 0.17 (pass/fail without values), jscpd (needs Node), xenon (only thresholds on top of radon).

### 3. Abgebildete Smells

All CodeScene criteria named in the task (function, implementation, module, tests) are covered; mapping and thresholds are in the table under [Score](#score). Added: `cognitive-complexity` (not a CodeScene smell, but asked for). Not covered: String Heavy Function Arguments and Missing Arguments Abstractions (not defined by CodeScene; partly covered by `primitive-obsession`), Lines of Declarations, Global Conditionals and Deep Global Nested Complexity (no meaning for Python modules; shell top-level code is checked as the pseudo-function `<top-level>` for complexity, nesting and conditions), Large Embedded Code Block (defined for Elixir only). Switched off per part: arguments, primitive obsession and cohesion for tests (pytest fixtures arrive as arguments); arguments, types and classes for shell (they do not exist there).

### 4. Schwellen, Gewichte und Score-Formel

Formula and thresholds: see [Score](#score) and [code-health.toml](../code-health.toml). Linear deduction per smell with a cap, the sum subtracted from 10, minimum 1. CodeScene publishes neither its formula nor its weights, so every `base`/`step`/`max` is an assumption.

### 5. Bedienung

`python3 -m code_health` or `uvx nox -s code-health` (the repository's task runner is nox). Table output, `--json` for agents, `--changed [BASE]` for changed files only (default: merge base with `origin/main`), `--all` to include files without smells. About 4 s for the whole repository; part scores are always computed over all files.

### 6. Gate

See [Gate, baseline and suppressions](#gate-baseline-and-suppressions): pre-commit hook `code-health` (`--gate --base HEAD` on the staged files), CI step in the `unit` job (`--gate --changed origin/main`), ratchet in `code-health-baseline.json`, suppressions only inline with a reason.

### 7. Ergebnis

Before (2026-11-23, first measurement with these rules): `python-cli` 3.76, `python-tests` 6.49, `shell` 8.10, `ansible` 8.65, overall 5.70; 85 files below 9.5. Worst files: `tests/unit/test_update_and_env.py`, `tests/unit/test_host_profiles.py`, `machine_cli/updates.py`, `machine_cli/commands.py`, `machine_cli/ssh_client.py` (all 1.0).

After: added once the refactorings are done.

### 8. Skills

Searched with `npx skills find` (python, refactoring, code quality, clean code, complexity, testing, pytest, ansible, shell, bash, shellcheck, code review). Adopted, project-local under `.claude/skills/` and pinned in `skills-lock.json`: `wondelai/skills@refactoring-patterns` (Fowler catalogue, green - small step - green loop) and `wshobson/agents@python-testing-patterns` (pytest patterns). Checked and rejected: `codehealth-mcp` (needs the paid CodeScene token), `juliusbrussee/caveman@safe-refactor` (good but trivial, unknown origin), `wshobson/agents@bash-defensive-patterns` (a blanket `set -Eeuo pipefail` changes behaviour), `github/awesome-copilot@refactor-method-complexity-reduce` (Copilot placeholders, C#-centric), `github/awesome-copilot@pytest-coverage` (pushes for 100 % coverage), `mattpocock/skills@code-review` and `addyosmani/agent-skills@code-review-and-quality` (overlap with the built-in `/code-review`), `akin-ozer/cc-devops-skills@ansible-validator` (much foreign script code), `kucherenko/jscpd@dry-refactoring` (fetches npm at run time).

### 9. Erfahrungen

Added once the refactorings are done.
