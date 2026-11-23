# Proposal

## Why

Agents change this repository often. According to CodeScene's whitepaper "AI-Ready Code" (A. Tornhill, 2026), AI changes in unhealthy code have at least 60 % more defects; the underlying study only covered code with a health of 7 or more. Healthy code is therefore a precondition for agents to work reliably, next to tests, coverage and review. The owner decided not to use the proprietary CodeScene score (paid token) and to compute an own score from 1 to 10 with free tools instead, modelled on CodeScene Code Health. Each part of the repository shall reach at least 9.5, with 10 as the target, and agents shall be able to develop against the checker.

## What Changes

- New checker `code-health` (Python package `code_health`, standard library only): scores every Python file and every shell script with logic from 1 to 10. Each file starts at 10.0, each smell deducts a configured amount, the minimum is 1.0.
- Separate parts with their own rules, score and target of 9.5: `python-cli` (measured like an application), `python-tests`, `shell` and `ansible` (owner direction, 2026-11-23). An LOC-weighted overall score is shown for information; the worst file is named.
- Smells modelled on CodeScene: complex method, large method, brain method, excess arguments, constructor over-injection, primitive obsession, code duplication, deep nested complexity, bumpy road, complex conditional, cognitive complexity, large file, overall code complexity, many functions, brain class, low cohesion (LCOM4), large assertion blocks and duplicated assertion blocks.
- `code-health.toml` holds the versioned scope, thresholds and deductions. Thresholds follow the published CodeScene Python defaults; own values are marked as assumptions.
- Command: `uvx nox -s code-health` (also `python3 -m code_health`): table with file, score and smells with line numbers; `--json` for agents; `--changed [BASE]` for changed files only.
- Gate in pre-commit and CI: every changed file must score at least 9.5 and must not get worse, and no part score may fall. While the repository is below 9.5, a ratchet baseline `code-health-baseline.json` holds the current scores of the files below 9.5; they must not fall below their entry.
- Suppressions only per inline comment `code-health: ignore[<rule>] <reason>`; a suppression without a reason or without a matching smell fails.
- `AGENTS.md` gets a section: run `code-health --changed` before every commit and fix smells instead of suppressing them. `docs/code-health.md` documents rules, score and gate, with the section "Steckbrief Code Health" for the comparison with the other repositories.
- Refactorings without behaviour change, in small tested steps, starting with the hotspots that change most often, until every part scores at least 9.5. All of them belong to this change, not to follow-up changes (owner decision, 2026-11-23).
- Agent skills `wondelai/skills@refactoring-patterns` and `wshobson/agents@python-testing-patterns` from skills.sh, installed project-locally (owner decision, 2026-11-23).

## Capabilities

### New Capabilities
- `code-health`: the code health score per part, its rules and configuration, the command and its output, the pre-commit and CI gate, the ratchet baseline and the suppression comments.

### Modified Capabilities
None. The new pre-commit hook and CI step are specified in `code-health`; the existing hook list in `pre-commit-checks` and the CI job list in `tests-and-ci` stay valid.

Affected profiles: none. The checker runs only in the repository (development, pre-commit, CI); nothing is installed or linked on hosts.

## Impact

- New: `code_health/` (package), the two skills under `.claude/skills/`, `code-health.toml`, `code-health-baseline.json`, `docs/code-health.md`, unit tests `tests/unit/test_code_health*.py`, nox session `code-health`, local pre-commit hook `code-health`, a CI step in `verify.yml`.
- Changed: `AGENTS.md`, `noxfile.py`, `.pre-commit-config.yaml`, `.github/workflows/verify.yml`, `Readme.md`/`docs/testing.md` (command). Refactorings touch `machine_cli/`, scripts under `home/`, `ansible/roles/*/files/` and `tests/` without changing behaviour.
- Dependencies: none at runtime; Python 3.11 or newer (`tomllib`). radon and complexipy (MIT) were used once to cross-check the metrics, they are not dependencies.

Where: this checkout `/home/ditschi/dotfiles/.claude/worktrees/xenodochial-ellis-c9a21e` on branch `code-health`. It is a git worktree that is not the live checkout, and AGENTS.md says to stay in a non-live checkout instead of creating another worktree. The refactorings touch `machine_cli` and shell scripts that run on the live host, so the work must not happen in the live checkout.
