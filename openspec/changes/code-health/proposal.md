# Proposal

## Why

Agents change this repository often. According to CodeScene's whitepaper "AI-Ready Code" (A. Tornhill, 2026), AI changes in unhealthy code have at least 60 % more defects; the underlying study only covered code with a health of 7 or more. Healthy code is therefore a precondition for agents to work reliably, next to tests, coverage and review. The owner decided not to use the proprietary CodeScene score (paid token) and to measure code health with free tools instead, modelled on CodeScene Code Health, with the target score 10 (no finding) and 9.5 as the minimum on the way there. Agents shall be able to develop against the check.

After comparing approaches across six repositories, the owner decided on 2026-11-23 to use ai-health for Python in all repositories and for shell where it occurs, with one shared strict profile. The own checker built first in this change was removed once ai-health was in place, following the owner's rule of no own logic where a tool exists (2026-11-24).

## What Changes

- ai-health (github.com/epatel/ai-health, MIT, deterministic, no AI needed) pinned to commit `033d1867fe514867d944d9387ee72db0188eed47` (v0.4.0) in one place, `scripts/aihealth`, which only runs it through `uvx` and passes the arguments through.
- Components with their own score: `python-cli` (all Python outside `tests/`, `openspec/` and the third-party skills), `python-tests` (`tests/`), `shell` (sh, bash and zsh files ai-health detects). Ansible has no score; ansible-lint stays its gate (owner decision Q3). Python scripts without a file extension (`machine_cli/machine`, `ssh-route`, `ssh-tunnel`, `work-net`, `homelab-ci`) are a documented gap while epatel/ai-health#3 is open (owner decision Q16).
- Profile "strict" in `.aihealth.toml` (CodeScene thresholds, `decay = 8`, `density_loc = 100000`, `delta.tolerance = 0`; owner decision Q15); `.aihealth-tests.toml` repeats it and switches off the argument, primitive and cohesion smells for tests.
- Commands: `uvx nox -s code-health` (scan report per component) and `scripts/aihealth delta --config <component config>` for the changed files, with `--format json` for agents.
- Gate: pre-commit hook `aihealth delta --staged` per component (exit 1 on any degradation; new files must have no smell); CI `delta` against the merge base with `main` per component and a comparison of the component scores of merge base and head (owner decision Q6); the tree-sitter grammars are cached in CI.
- Suppressions only file-wide as `# aihealth: disable=<smell> -- <reason>`; a pygrep hook rejects them without a reason.
- ruff replaces black and flake8 as the Python linter and formatter, in its own commit; its structure rules (`C90`) stay off, ai-health is the only source for each smell (owner decisions Q8, Q9).
- The own checker (`code_health/`, `code-health.toml`, `code-health-baseline.json`, its tests) is removed; its measurements are recorded in design.md and the Steckbrief (owner rule, 2026-11-24: no own logic where a tool exists).
- `AGENTS.md` and `docs/code-health.md` describe the ai-health workflow; the docs carry the "Steckbrief Code Health" for the comparison across repositories.
- Refactorings without behaviour change toward score 10, in small tested steps, ordered by change frequency; refactorings beyond those already running need the owner's approval of the ai-health hotspots.
- Agent skills from skills.sh, installed project-locally: `wondelai/skills@refactoring-patterns`, `wshobson/agents@python-testing-patterns`, `obra/superpowers@systematic-debugging`, `verification-before-completion` and `receiving-code-review`, `mattpocock/skills@writing-for-agents`, `github/awesome-copilot@github-actions-hardening` (owner decisions, 2026-11-23 and 2026-11-24).
- Two pull requests: first the gate, tooling, docs and skills; then the refactorings (owner decision, 2026-11-24).

## Capabilities

### New Capabilities
- `code-health`: the code health check with ai-health: components, profile, commands, gate, suppressions and documented gaps.

### Modified Capabilities
- `pre-commit-checks`: the hook list names ruff instead of black and flake8, plus the ai-health hooks.

Affected profiles: none. The check runs only in the repository (development, pre-commit, CI); nothing is installed or linked on hosts.

## Impact

- New: `scripts/aihealth`, `scripts/aihealth_components.py`, `.aihealth.toml`, `.aihealth-tests.toml`, `ruff.toml`, `docs/code-health.md`, the two skills under `.claude/skills/` with `skills-lock.json`, unit tests for the configuration consistency.
- Changed: `AGENTS.md`, `noxfile.py`, `.pre-commit-config.yaml`, `.github/workflows/verify.yml`, `Readme.md`, `docs/testing.md`; the ruff migration reformats Python files without changing behaviour. Refactorings touch `machine_cli/`, scripts under `home/`, `ansible/` and `tests/` without changing behaviour.
- Dependencies: ai-health and tree-sitter-language-pack (about 30 MB of grammars, cached) via `uvx`, only for development and CI; ruff via pre-commit.

Where: this checkout `/home/ditschi/dotfiles/.claude/worktrees/xenodochial-ellis-c9a21e` on branch `code-health`. It is a git worktree that is not the live checkout, and AGENTS.md says to stay in a non-live checkout instead of creating another worktree. The refactorings touch `machine_cli` and shell scripts that run on the live host, so the work must not happen in the live checkout.
