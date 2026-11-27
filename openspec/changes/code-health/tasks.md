# Tasks

## 1. Own checker (history; removed in 6.1)

- [x] 1.1 Apply the decisions (complex conditional from 2 operators, primitive obsession over annotated arguments) to `code-health.toml` and the rules; verify with `python3 -m code_health` that the run completes and the config comments state each value's origin
- [x] 1.2 Parts `python-cli`, `python-tests`, `shell` with their own rule sets in `code-health.toml` (table, JSON, baseline and gate per part, overall score for information) and the `ansible` part (tasks per file, complex `when`, `block` nesting, Jinja control tags, duplicated tasks); verify with `python3 -m code_health` that each part score is shown and that `excess-arguments` is not reported for tests
- [x] 1.3 Unit tests for the Python metrics (cyclomatic and cognitive complexity, nesting with `elif`, bumps, conditionals, arguments, primitive arguments, LCOM4, assertion blocks, nested functions excluded from duplication) in `tests/unit/test_code_health_python.py`; verify with `pytest tests/unit/test_code_health_python.py -q`
- [x] 1.4 Unit tests for the shell parser (functions in all three definition styles, nesting, `case` items, heredocs, keywords inside strings and comments, files without logic) in `tests/unit/test_code_health_shell.py`; verify with `pytest tests/unit/test_code_health_shell.py -q`
- [x] 1.5 Unit tests for rules, scoring, suppressions, `--json`, `--changed` and the gate and baseline on a temporary git repository in `tests/unit/test_code_health.py`; verify with `pytest tests/unit/test_code_health.py -q`
- [x] 1.6 Refactor `code_health/` until every file scores 10.0; verify with `python3 -m code_health code_health/*.py --all`
- [x] 1.7 Write `docs/code-health.md` (rules, thresholds with origin, formula, gate, baseline, suppressions, commands) with the section "Steckbrief Code Health" and its nine headings (Messumfang, Tools und Versionen, Abgebildete Smells, Schwellen/Gewichte/Formel, Bedienung, Gate, Ergebnis, Skills, Erfahrungen) and link it from `Readme.md` and `docs/testing.md`; verify the documented commands run as written

## 2. Gate with the own checker (history; replaced in group 3, removed in 6.1)

- [x] 2.1 Add the nox session `code-health` (passes arguments through); verify `uvx nox -s code-health -- --changed` prints the table
- [x] 2.2 Generate `code-health-baseline.json` with `python3 -m code_health --update-baseline`; verify `python3 -m code_health --gate --changed` passes on the branch
- [x] 2.3 Add the local pre-commit hook `code-health` (`--gate --base HEAD` on the staged files, serial); verify it fails on a scratch commit that adds a complex function and passes after reverting
- [x] 2.4 Add the gate step to the `unit` job in `verify.yml` (`--gate --changed origin/main`, full fetch depth); verify the workflow YAML with `pre-commit run check-yaml --files .github/workflows/verify.yml`
- [x] 2.5 Add the section "Code health" to `AGENTS.md`: run `python3 -m code_health --changed` before every commit, fix smells instead of suppressing them, suppress only with a reason, tighten the baseline after improvements; add a rule for behaviour-preserving refactoring
- [x] 2.6 Install `wondelai/skills@refactoring-patterns` and `wshobson/agents@python-testing-patterns` project-locally with `npx skills add`; verify they appear under `.claude/skills/` and their SKILL.md matches the reviewed version

## 3. ai-health

- [x] 3.1 Add `scripts/aihealth` with the pinned commit `033d1867fe514867d944d9387ee72db0188eed47` as the only pin; subcommands pass `--config` per component (`scan`, `delta` for `python-cli`/`shell` with `.aihealth.toml` and for `python-tests` with `.aihealth-tests.toml`); verify `scripts/aihealth scan` and `scripts/aihealth delta --format json` run and the wrapper itself has no findings
- [x] 3.2 Add `.aihealth.toml` and `.aihealth-tests.toml` (profile strict) and `tests/unit/test_aihealth_config.py`, which checks that `[thresholds]`, `[score]` and `[delta]` are equal and the three test weights are 0; verify with `pytest tests/unit/test_aihealth_config.py -q`
- [x] 3.3 Add `scripts/aihealth_components.py` (component scores of a revision from the scan JSON; compare merge base and head, tolerance 0.01) with unit tests for the comparison; verify with its tests and a run against `HEAD~1`
- [x] 3.4 Change the nox session `code-health` to print the ai-health scan per component; verify `uvx nox -s code-health`
- [x] 3.5 Add the pre-commit hooks `aihealth-delta` (`scripts/aihealth delta --staged`, `language: system`) and `aihealth-suppression-reason` (pygrep); verify the delta hook fails on a scratch change that adds a complex function and passes after reverting, and the pygrep hook fails on a suppression without ` -- <reason>`
- [x] 3.6 Add the CI steps: grammar cache, `delta` against the merge base per component, component comparison, scan report; verify with `pre-commit run check-yaml --files .github/workflows/verify.yml` and a local run of the same commands
- [x] 3.7 Rewrite `docs/code-health.md` for ai-health (components, profile, commands, gate, suppressions, gaps: scripts without extension, Ansible, test smells), update the Steckbrief, `AGENTS.md`, `Readme.md` and `docs/testing.md`; verify the documented commands run as written

- [x] 3.8 Cut `scripts/aihealth` back to the pin (hooks, CI and nox pass `--config` per component themselves) and drop the cosmetic type aliases in `scripts/aihealth_components.py`; verify the hooks fail and pass on scratch changes and `scripts/aihealth scan scripts/aihealth_components.py --config .aihealth.toml` shows no finding
- [x] 3.9 Install `obra/superpowers@systematic-debugging`, `verification-before-completion`, `receiving-code-review`, `mattpocock/skills@writing-for-agents` and `github/awesome-copilot@github-actions-hardening` project-locally; verify their SKILL.md match the reviewed copies

## 4. ruff

- [x] 4.1 Add `ruff.toml` (format line length 88 as black, lint line length 120 as flake8, rules `E`, `F`, `W`, no `C90`) and replace the `black` and `flake8` hooks with `ruff-format` and `ruff` (check); verify `pre-commit run ruff --all-files` and `pre-commit run ruff-format --all-files` pass after 4.2
- [x] 4.2 Reformat with `ruff format` and fix `ruff check` findings in one separate commit without behaviour change, after the running refactorings landed; verify `pytest tests/unit -q`

## 4b. Pull request 1

- [x] 4b.1 Open PR 1 (gate, profiles, ruff, docs, skills) without the refactorings; run an independent review (`/code-review` high or a fresh reviewer subagent with only the diff, the repo and AGENTS.md), fix or justify findings, wait for green CI (`gh pr checks`), and merge only after the owner's go in this session

## 5. Refactoring toward 10 (pull request 2)

- [x] 5.1 Land the running refactorings (`machine_cli/updates.py`, `machine_cli/commands.py`, shell scripts, Ansible task files), each reviewed and committed per file with its tests green; verify per file with its tests and `scripts/aihealth delta`
- [ ] 5.2 Present the ai-health hotspots (strict) to the owner and get approval for the further refactorings
- [ ] 5.3 Refactor the approved files toward 10, ordered by change frequency, one file or topic per commit; verify per file with its tests and `scripts/aihealth delta`, until every component scores at least 9.5

## 6. Removal of the own checker

- [x] 6.1 Remove (owner rule 2026-11-24, in PR 1) `code_health/`, `code-health.toml`, `code-health-baseline.json`, its tests and nox session; verify `pytest tests/unit -q` and that no reference is left

## 7. Validation

- [ ] 7.1 `pytest tests/unit -q` (shared test and validation config and `machine_cli` core change)
- [ ] 7.2 `pre-commit run --files <changed paths>` including the new untracked files, then `pre-commit run --all-files` because the hook configuration changes
- [ ] 7.3 `openspec validate code-health --strict`
- [ ] 7.4 Review the branch diff against main with a fresh reviewer (`/code-review` or a review subagent) and fix the findings

## Workflow follow-up

- Fill in "7. Ergebnis" and "9. Erfahrungen" of the Steckbrief, report scores before and after per component, remaining findings and the Steckbrief path, and open the PR.
- Archive the change after review (`/opsx:archive`).
