# Design

## Context

See proposal.md - Why.

Inventory before this change:
- Linters in pre-commit: `black`, `flake8` (max line length 120, no complexity plugin), `shellcheck` (bash and sh, zsh excluded), `shfmt` (4 spaces), `yamlfmt`, `codespell`, `detect-secrets`, hygiene hooks, local hooks (`gitconfig-no-host-settings`, `bashrc-no-managed-blocks`, `mise-tools-declared-once`, `openspec-specs-strict`, `no-co-authored-by`). No complexity or size limits anywhere; no `pyproject.toml`, no ruff, no isort.
- Task runner: `noxfile.py` with uv venvs (`compile`, `tests`, `ansible`, `docker`). CI: `.github/workflows/verify.yml` (unit tests amd64/arm, pre-commit `--all-files`, ansible-lint on relevant changes, Docker and APT jobs).
- Code: 118 Python files (29 000 lines of code without blank lines, comments and docstrings; `machine_cli/` 9 700, `tests/` 17 000), 42 shell files (2 100 lines), 14 Ansible roles (1 774 lines of task files). The host setup is untouched: the check runs only in the repository.

Measurements on 2026-11-23:
- Own checker (first step of this change, CodeScene thresholds, own deductions): `python-cli` 3.76, `python-tests` 6.49, `shell` 8.10, `ansible` 8.65; 85 files below 9.5.
- ai-health with the strict profile on `main` (0a3d695): `python-cli` 3.97, `python-tests` 6.30, `shell` 8.89. While the first refactorings were in progress the branch measured `python-cli` 4.76 (62 files, 41 with findings), `python-tests` 6.43, `shell` 9.56. A full scan takes about 3 s. The hotspots match the own checker: `tests/unit/test_update_and_env.py` (46 changes in 12 months, 1.28), `tests/unit/test_host_profiles.py` (44, 1.62), `machine_cli/updates.py` (30, 1.04), `tests/unit/test_bw_and_answers.py` (24, 7.0), `tests/unit/test_machine_cli.py` (22, 5.26), `machine_cli/tools.py` (17, 2.82), `machine_cli/dotfiles.py` (17, 3.79), `tests/unit/test_zsh_handoff.py` (15, 2.77); largest gaps to 10 also in `machine_cli/ssh_client.py`, `env_pull.py`, `netrc_sync.py`, `bw_client.py`.
- ai-health does not detect Python scripts without an extension (`machine_cli/machine`, `home/core/.local/bin/ssh-route`, `home/ssh-tunnel/.local/bin/ssh-tunnel`, `home/work/.local/bin/work-net`, `ansible/roles/homelab_node/files/homelab-ci`); epatel/ai-health#3 asks for shebang detection. In git repositories it lists files through `git ls-files`, so hidden directories such as `home/core/.local/bin` and `home/core/.shell` are scored.
- ai-health has no test detection for Python and supports suppressions only per file (`# aihealth: disable=<smell> -- <reason>`; without ` -- ` the reason becomes part of the smell name and the suppression silently does nothing).

## Goals / Non-Goals

**Goals:**
- One shared tool and profile for Python across the owner's repositories (owner decision Q2), with score 10 as the target.
- One command with machine-readable output and a mode for changed files, which agents develop against.
- An agent-proof gate: per file against the base revision and per component in CI.
- A section "Steckbrief Code Health" in `docs/code-health.md` with the nine headings requested by the owner, for the comparison with the other repositories.

**Non-Goals:**
- A score for Ansible (owner decision Q3); ansible-lint stays its only gate.
- Test-specific smells (large and duplicated assertion blocks): ai-health has none; they are a documented gap until upstream adds them (owner decision Q4).
- Keeping the own checker as a cross-check; it is removed.

## Decisions

**ai-health as the tool, pinned to a commit.** ai-health (MIT) is deterministic, covers Python and shell with CodeScene-like smells, has `scan`, `delta` with exit codes and JSON, and Claude Code hooks (owner decision Q1). It is pinned to commit `033d1867fe514867d944d9387ee72db0188eed47` (the commit behind v0.4.0) rather than the tag: with the tag `uvx` resolves over the network on every call (about 1.6 s), with the commit everything comes from the cache (about 0.24 s, also offline). The pin lives only in `scripts/aihealth`, a three-line script that runs ai-health through `uvx` and passes every argument through; hook, CI and nox call it with an explicit `--config` per component, so there is no second copy of the pin in a lock file or in pre-commit's `additional_dependencies`. The pre-commit hooks therefore use `language: system`; a `language: python` hook would need a second pin. An earlier version of the wrapper also split paths per component and merged the JSON of both; it was cut back because ai-health does all of that per call (owner rule, 2026-11-24: no own logic where the tool can do it).

**Components.** `python-cli` (everything outside `tests/`, `openspec/` and the third-party skills in `.claude/skills/`), `python-tests` (`tests/`) and `shell`. The main scan with `.aihealth.toml` covers Python and shell together; the component scores are computed from its JSON per language (shell = bash, zsh, sh), as the LOC-weighted mean ai-health also uses for its project score. Tests are scanned separately with `.aihealth-tests.toml`.

**Profile strict in two files.** `.aihealth.toml` holds the profile (owner decision Q15): CodeScene thresholds (ai-health's defaults for complex method 9, large method 70, nesting 4, bumpy road 2, complex conditional 2 and arguments 4 already match), `large_file = 600`, `primitive_obsession = 0.3`, `decay = 8` (stricter than the default 15; matches the own prototypes), `symbol_cap = 4`, `density_loc = 100000` (large files are not relieved through their smell density), `delta.tolerance = 0`. ai-health reads exactly one file per call, so `.aihealth-tests.toml` repeats the profile and only adds `[weights]` 0 for `excess_arguments` (pytest fixtures arrive as arguments), `primitive_obsession` and `low_cohesion` (test classes group cases). A unit test keeps `[thresholds]`, `[score]` and `[delta]` of both files equal, so the profile is changed in one place and the test points at the other. Every call passes `--config` explicitly, because `aihealth scan <dir>` otherwise reads `<dir>/.aihealth.toml` and silently falls back to the defaults.

For the own checker the owner had first chosen 50 % for primitive obsession; the strict profile for ai-health sets 30 % for production code and switches the smell off in test code (owner decisions Q15 and Q18).

**Gate.** Locally the pre-commit hook runs `delta --staged` for both configurations (exit 1 on any degradation; a new file with a finding counts as degraded). In CI, `delta --base "$(git merge-base origin/main HEAD)" --head HEAD` runs per configuration with full fetch depth; against `origin/main` a branch behind `main` would be charged with `main`'s newer changes. CI also compares the component scores of merge base and head (owner decision Q6): `scripts/aihealth_components.py` exports the merge base with `git archive`, scans both trees and fails when a component drops by more than 0.01; the small tolerance absorbs the deletion of a healthy file, which can lower a mean. `delta` does not see cross-file duplication, so the CI also prints the full scan of each component as a report. The tree-sitter grammars (`~/.cache/tree-sitter-language-pack`, about 30 MB) are cached in CI.

**Suppressions.** ai-health supports only file-wide suppressions. The pygrep hook `aihealth-suppression-reason` rejects `aihealth: disable=` unless it is followed by smell names, ` -- ` and a reason of at least ten characters (regex `aihealth:[ \t]*disable=(?![\w, \t]+-- .{10})`), the same as in homelab; no own code is needed.

**ruff replaces black and flake8.** One linter and formatter for Python in all repositories (owner decision Q8), in its own commit so the reformatting can be reviewed separately. `ruff format` (black-compatible) and `ruff check` with the rules flake8 enforced today (`E`, `F`, `W`, maximum line length 120); `C90` and other structure rules stay off, because ai-health is the only source for each smell (owner decision Q9). isort is not used in this repository, so import sorting is not added.

**Own checker removed.** The checker built first (`code_health/`, standard library plus PyYAML, own deductions) measured the same hotspots as ai-health and was removed with its config, baseline and tests once ai-health was in place (owner rule, 2026-11-24: no own logic where a tool exists, it does not stay as a cross-check). Its measurements are kept in Context and in the docs' Steckbrief.

**Component comparison is the only own logic.** `scripts/aihealth_components.py` (about 95 lines of code) exists because ai-health cannot compare component scores between two revisions (owner decision Q6); everything else is plain ai-health calls.

**Commands.** The task runner is nox: `uvx nox -s code-health` prints the scan of each component and their scores; agents and humans check changed files with `scripts/aihealth delta --config <component config>` (`--format json`).

**Two skills from skills.sh, project-local.** `wondelai/skills@refactoring-patterns`, `wshobson/agents@python-testing-patterns`, `obra/superpowers@systematic-debugging`, `obra/superpowers@verification-before-completion`, `obra/superpowers@receiving-code-review`, `mattpocock/skills@writing-for-agents` and `github/awesome-copilot@github-actions-hardening` are installed under `.claude/skills/` and pinned in `skills-lock.json` (owner decisions, 2026-11-23 and 2026-11-24). Their SKILL.md files were read before; pre-commit excludes them so they stay byte-identical to the pinned source. Skills from `codehealth-mcp` were excluded because they need the paid CodeScene token.

**Two pull requests.** The first carries the ai-health gate, the profiles, ruff, the docs and the skills; the second the refactorings toward 10, after the owner approved the ai-health hotspots (owner decision, 2026-11-24). Each gets an independent review, green CI and the owner's go before it is merged.

**Type hints stay.** Type hints are never removed or weakened and no type aliases are added only to silence a smell; a finding is fixed with a parameter object or dataclass where that improves the code, otherwise it stays or gets a file-wide suppression with a reason (owner rule, 2026-11-24). Primitive obsession is off in test code and stays at 30 % in production code (owner decision Q18, 2026-11-24).

**Refactorings.** Behaviour-preserving, in small steps with the tests of the touched code green before and after, one file or one topic per commit, ordered by change frequency. The first four (updates, commands, shell scripts, Ansible task files) started against the own checker and fix findings ai-health reports as well; further refactorings toward 10 start after the owner approved the ai-health hotspots.

## Risks / Trade-offs

- [Upstream changes or disappears] → Pinned commit; `scripts/aihealth` is the only place to change.
- [No network in CI or on a host] → Grammar cache in CI; locally the first run downloads, later runs work offline from the uv and grammar caches.
- [Scripts without extension are not scored] → Documented gap until epatel/ai-health#3 is solved; their size and complexity are known from the own checker's measurement.
- [Two profile files drift apart] → Unit test compares them.
- [Strict gate blocks unrelated small edits in unhealthy files] → `delta` only fails when a file gets worse, not because it is already unhealthy.
- [Refactoring breaks behaviour] → Small steps, each with the unit tests green; tests for the touched code first where coverage is thin.

## Migration Plan

No host changes. Order: ai-health wrapper, profiles, nox session, hooks and CI, docs; ruff migration as its own commit after the running refactorings landed; then, after the owner's approval of the hotspots, refactorings toward 10; the own checker is removed in the first pull request. Rollback: remove the ai-health hooks and CI steps.
