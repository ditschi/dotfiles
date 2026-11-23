# Tasks

## 1. Checker

- [x] 1.1 Apply the decisions (complex conditional from 2 operators, primitive obsession over annotated arguments) to `code-health.toml` and the rules; verify with `python3 -m code_health` that the run completes and the config comments state each value's origin
- [x] 1.2 Parts `python-cli`, `python-tests`, `shell` with their own rule sets in `code-health.toml` (table, JSON, baseline and gate per part, overall score for information) and the `ansible` part (tasks per file, complex `when`, `block` nesting, Jinja control tags, duplicated tasks); verify with `python3 -m code_health` that each part score is shown and that `excess-arguments` is not reported for tests
- [x] 1.3 Unit tests for the Python metrics (cyclomatic and cognitive complexity, nesting with `elif`, bumps, conditionals, arguments, primitive arguments, LCOM4, assertion blocks, nested functions excluded from duplication) in `tests/unit/test_code_health_python.py`; verify with `pytest tests/unit/test_code_health_python.py -q`
- [x] 1.4 Unit tests for the shell parser (functions in all three definition styles, nesting, `case` items, heredocs, keywords inside strings and comments, files without logic) in `tests/unit/test_code_health_shell.py`; verify with `pytest tests/unit/test_code_health_shell.py -q`
- [x] 1.5 Unit tests for rules, scoring, suppressions, `--json`, `--changed` and the gate and baseline on a temporary git repository in `tests/unit/test_code_health.py`; verify with `pytest tests/unit/test_code_health.py -q`
- [ ] 1.6 Refactor `code_health/` until every file scores 10.0; verify with `python3 -m code_health code_health/*.py --all`
- [x] 1.7 Write `docs/code-health.md` (rules, thresholds with origin, formula, gate, baseline, suppressions, commands) with the section "Steckbrief Code Health" and its nine headings (Messumfang, Tools und Versionen, Abgebildete Smells, Schwellen/Gewichte/Formel, Bedienung, Gate, Ergebnis, Skills, Erfahrungen) and link it from `Readme.md` and `docs/testing.md`; verify the documented commands run as written

## 2. Gate

- [x] 2.1 Add the nox session `code-health` (passes arguments through); verify `uvx nox -s code-health -- --changed` prints the table
- [x] 2.2 Generate `code-health-baseline.json` with `python3 -m code_health --update-baseline`; verify `python3 -m code_health --gate --changed` passes on the branch
- [x] 2.3 Add the local pre-commit hook `code-health` (`--gate --base HEAD` on the staged files, serial); verify it fails on a scratch commit that adds a complex function and passes after reverting
- [x] 2.4 Add the gate step to the `unit` job in `verify.yml` (`--gate --changed origin/main`, full fetch depth); verify the workflow YAML with `pre-commit run check-yaml --files .github/workflows/verify.yml`
- [x] 2.5 Add the section "Code health" to `AGENTS.md`: run `python3 -m code_health --changed` before every commit, fix smells instead of suppressing them, suppress only with a reason, tighten the baseline after improvements; add a rule for behaviour-preserving refactoring
- [x] 2.6 Install `wondelai/skills@refactoring-patterns` and `wshobson/agents@python-testing-patterns` project-locally with `npx skills add`; verify they appear under `.claude/skills/` and their SKILL.md matches the reviewed version

## 3. Refactoring up to 9.5

- [ ] 3.1 `machine_cli/updates.py`: split `_update_steps`, `update_plan` and the other smells into small functions without behaviour change; verify with `pytest tests/unit/test_update_and_env.py tests/unit/test_machine_cli.py -q` and a score of at least 9.5
- [ ] 3.2 `machine_cli/commands.py`: split `cmd_setup`, `cmd_apply` and `cmd_status`; verify with `pytest tests/unit -q -k "setup or apply or status or machine_cli"` and a score of at least 9.5
- [ ] 3.3 All other files below 9.5, ordered by change frequency (`tests/unit/test_update_and_env.py`, `tests/unit/test_host_profiles.py`, `machine_cli/tools.py`, `machine_cli/dotfiles.py`, ...), one file per commit; verify per file with its tests and a score of at least 9.5, until every part scores at least 9.5
- [ ] 3.4 After each step tighten the baseline with `python3 -m code_health --update-baseline` and verify the gate passes

## 4. Validation

- [ ] 4.1 `pytest tests/unit -q` (shared test and validation config and `machine_cli` core change)
- [ ] 4.2 `pre-commit run --files <changed paths>` including the new untracked files, then `pre-commit run --all-files` because the hook configuration changes
- [ ] 4.3 `openspec validate code-health --strict`
- [ ] 4.4 Review the branch diff against main with a fresh reviewer (`/code-review` or a review subagent) and fix the findings

## Workflow follow-up

- Fill in "7. Ergebnis" and "9. Erfahrungen" of the Steckbrief, report scores before and after per part, remaining smells and the Steckbrief path, and open the PR.
- Archive the change after review (`/opsx:archive`).
