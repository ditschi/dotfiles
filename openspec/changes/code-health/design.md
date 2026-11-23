# Design

## Context

See proposal.md - Why.

Inventory before this change:
- Linters in pre-commit: `black`, `flake8` (max line length 120, no complexity plugin), `shellcheck` (bash and sh, zsh excluded), `shfmt` (4 spaces), `yamlfmt`, `codespell`, `detect-secrets`, hygiene hooks, local hooks (`gitconfig-no-host-settings`, `bashrc-no-managed-blocks`, `mise-tools-declared-once`, `openspec-specs-strict`, `no-co-authored-by`). No complexity or size limits anywhere; no `pyproject.toml`, no ruff.
- Task runner: `noxfile.py` with uv venvs (`compile`, `tests`, `ansible`, `docker`). CI: `.github/workflows/verify.yml` (unit tests amd64/arm, pre-commit `--all-files`, ansible-lint on relevant changes, Docker and APT jobs).
- Code: 118 Python files (29 000 lines of code without blank lines, comments and docstrings; `machine_cli/` 9 700, `tests/` 17 000), 38 shell scripts with logic (1 900 lines), 6 shell files without logic. The host setup is untouched: the checker runs only in the repository.

First score of the prototype (2026-11-23, one rule set for everything, before the split into parts): overall 5.22; Python 5.0, shell 8.6; by area machine_cli 3.2, tests 6.1, other Python scripts 2.0, shell 8.6, the checker itself 8.3; 66 of 156 files at 9.5 or more. Top hotspots by changes in the last 12 months and score: `tests/unit/test_update_and_env.py` (46 changes, 1.0), `tests/unit/test_host_profiles.py` (44, 1.0), `machine_cli/updates.py` (30, 1.0), `tests/unit/test_bw_and_answers.py` (24, 5.2), `machine_cli/commands.py` (23, 1.0), `tests/unit/test_machine_cli.py` (22, 7.7), `machine_cli/machine` (22, 8.6), `machine_cli/tools.py` (17, 1.0), `machine_cli/dotfiles.py` (17, 3.2), `tests/unit/test_zsh_handoff.py` (15, 3.3). Largest share of the gap to 10: the two big test modules, `ssh_client.py`, `updates.py`, `work-net`, `env_pull.py`.

The published CodeScene defaults come from CodeScene's `default-rules.zip` (`code-health-rules.py.json`, May 2025), linked from the help center article on default thresholds. CodeScene does not publish its score formula, the criteria for brain method and brain class, an LCOM4 limit, or a threshold for the number of functions.

Ansible today: 14 roles, 53 YAML files, 1 774 lines in task files (largest `homelab_node/tasks/main.yml` with 479), 144 `when` conditions of which none has two or more `and`/`or`, 6 Jinja control tags in 28 templates. ansible-lint runs in CI on relevant changes.

## Goals / Non-Goals

**Goals:**
- A score from 1 to 10 per file and per part, at least 9.5 per part, target 10; each part measured by criteria that fit it (owner direction, 2026-11-23): the Python CLI like an application, tests like tests, shell scripts by their own criteria.
- One command with machine-readable output and a mode for changed files, which agents develop against.
- Metrics close to established tools, so the score is explainable: the cyclomatic complexity matches radon for 533 of 537 `machine_cli` functions, the cognitive complexity matches complexipy for 526 of 537 (the rest differ because complexipy adds nested functions to the outer one).
- A section "Steckbrief Code Health" in `docs/code-health.md` with the nine headings requested by the owner, for the later comparison with the other repositories.

**Non-Goals:**
- A shared implementation or shared command names with the other repositories; goals are shared, tools are chosen per repository (owner direction, 2026-11-23).
- Reproducing CodeScene's exact numbers; its formula is not public.
- Change coupling, hotspot history or knowledge metrics in the score.

## Decisions

**Parts with their own rules and their own target.** The scored files are split into parts by globs in `code-health.toml`, each with its own rule set, score, baseline value and target of 9.5 (owner direction, 2026-11-23):
- `python-cli`: `machine_cli/`, the Python programs under `home/` and `ansible/roles/*/files/`, `noxfile.py` and the checker itself. Measured like an application with the full CodeScene function, module and class rules.
- `python-tests`: `tests/`. Function rules for size and complexity, duplication, large and duplicated assertion blocks. Not measured: excess arguments (pytest fixtures arrive as arguments, so many arguments are the idiom, not a smell), primitive obsession and low cohesion (test classes group cases, they do not hold state).
- `shell`: sh, bash and zsh files with logic. Measured: complex method, large method, nesting, bumpy road, complex conditional, cognitive complexity, duplication, large file and the complexity of top-level code. Shell functions take no declared arguments and have no classes or types, so arguments, primitive obsession, brain class and low cohesion do not apply. Size limits are lower than for Python (assumption: function above 40 lines, file above 300), because shell has no modules or types to structure long code, and nesting fires from 3 (assumption), because nested shell blocks with quoting and exit codes are harder to follow than Python's. Correctness stays with shellcheck, which already gates in pre-commit.
- `ansible`: task files, handlers and templates of the roles and playbooks, with few metrics: tasks per task file (large file, assumption: more than 40 tasks), `when` with two or more `and`/`or` (complex conditional), nesting of `block`, Jinja control tags per template, duplicated tasks within a role (owner decision, 2026-11-23). No free tool gives Ansible a health score; scoring ansible-lint findings was rejected because they measure style and correctness, not complexity, and CI already keeps them at zero. ansible-lint stays the correctness gate.

**Overall score for information only.** The output also shows the LOC-weighted mean over all parts, because a single number is handy for trends, but the gate uses only the part scores: a large Python part would otherwise hide a falling shell part.

**Own analysis on the standard library for Python and shell.** Python is analysed with `ast` and `tokenize`; shell with a line-based parser that relies on the shfmt layout enforced by pre-commit. The Python ecosystem's tools were checked first: radon/xenon (MIT) cover cyclomatic complexity only, complexipy (MIT) cognitive complexity only, ruff's `C901`/`PLR09xx`/`PLR1702` give pass/fail without values, lizard (MIT) has no shell support and no nesting or bumpy-road data, jscpd needs Node. Combining them would mean four installs in pre-commit and CI and four output formats to get less than one AST pass gives; for shell no free tool measures complexity at all. radon and complexipy remain the reference for cross-checking the metrics in the tests.

**Thresholds for the Python parts from the CodeScene Python defaults.** Complex method above 9, large method above 70 lines, more than 4 arguments (constructors 5), nesting depth from 4, bumpy road from 2 bumps of depth 2, complex conditional from 2 `and`/`or` operators, file above 600 lines, mean cyclomatic complexity above 4, primitive arguments above 50 % (CodeScene: 30 %), duplication between functions of 10+ lines that are 75 % similar, large assertion blocks of 4 asserts with 4 such blocks per file. Own assumptions, confirmed as listed (owner decision, 2026-11-23) and marked in the config: cognitive complexity above 15 (SonarSource default), brain method = complex and large at once, brain class = large file with 20+ functions and a brain method, many functions above 40, low cohesion = LCOM4 of 2+ in classes with 4+ methods, duplicated assertion blocks = the same 2+ asserts in several tests, the shell values above, and every deduction.

**Complex conditional from 2 operators.** A branch condition with two or more `and`/`or` operators (`a and b and c`; in shell `&&`, `||`, `-a`, `-o` in an `if`/`while` condition) is a complex conditional, reading CodeScene's default of 2 as operators (owner decision, 2026-11-23). The rejected alternative, 4 operators, would be far more lenient than CodeScene.

**Primitive obsession counts annotated arguments only, from 50 %.** The share of `str`/`int`/`float`/`bool`/`bytes` arguments is taken over the annotated arguments, and a file is judged only with at least 10 of them (owner decision, 2026-11-23). Dropping the rule for Python was rejected; counting unannotated arguments would penalise type hints. The smell fires above 50 % instead of CodeScene's 30 % (owner decision, 2026-11-23): at 30 % it fired for 26 of 33 judged `python-cli` files, and fixing it would have meant a value type for nearly every argument, including plain numeric thresholds. At 50 % it flags files where most arguments are primitives (17 files), and domain values such as paths, hosts and revisions get their own types. Keeping 30 %, counting only string arguments (6 files) and dropping the rule were rejected.

**Two skills from skills.sh, project-local.** `wondelai/skills@refactoring-patterns` (Fowler catalogue, behaviour-preserving loop) and `wshobson/agents@python-testing-patterns` (pytest patterns) are installed in this repository (owner decision, 2026-11-23). Their SKILL.md files were read before: no remote scripts, no instructions to bypass checks. Skills from `codehealth-mcp` were excluded because they need the paid CodeScene token.

**Linear deductions with a cap per smell.** `min(max, base + step × excess)`; the sum is subtracted from 10, floor 1.0. This is simple to explain to an agent ("this smell costs 0.6") and lets one bad function cost more than a slightly large one. The per-smell cap stops a single extreme value from dominating.

**Token similarity for duplication.** Function bodies are compared as token sequences with literals normalised (`difflib.SequenceMatcher`), so copies that differ only in data count; nested functions are excluded from the outer function's tokens.

**Shell top-level code as a pseudo-function `<top-level>`.** Scripts often have their logic outside functions; it is checked for complexity, nesting, bumpy road and conditionals, but not for size, because rc files are long lists of settings.

**Gate compares against the base revision and the baseline.** A changed file must reach 9.5 and must not fall below its own score at the base revision (`HEAD` in pre-commit, merge base with `main` in CI); baseline files need at least their baseline score instead of 9.5. Every part score is computed on the full tree each run (about 5 s) and compared with its baseline value. The baseline only tightens; it is updated explicitly with `--update-baseline`.

**Command in nox, package at the repository root.** The repository's task runner is nox, so the command is `uvx nox -s code-health`; `python3 -m code_health` works without nox for the pre-commit hook and agents. Output is a table, `--json` for agents. `machine_cli` is deployed to hosts; the checker is a development tool, so it lives in `code_health/` next to it.

## Risks / Trade-offs

- [Assumed deductions make scores differ from CodeScene] → Every value is in the config with its origin; the formula is documented; recalibration is a config change.
- [The shell parser is heuristic] → It relies on shfmt formatting, which pre-commit enforces; unit tests cover functions, nesting, case items, heredocs and strings with keywords.
- [Rules that punish type hints] → Primitive obsession counts only annotated arguments, so unannotated code is neither punished nor rewarded.
- [Strict gate blocks unrelated small edits in unhealthy files] → Baseline files only need their baseline score, not 9.5; a fall in score is always a real new smell.
- [Full scan in every commit] → About 5 s; the duplication comparison dominates and can be limited to changed files if it becomes a burden.
- [Refactoring breaks behaviour] → Small steps, each with the unit tests green; tests for the touched code first where coverage is thin.

## Migration Plan

No host changes. Order: checker with parts, tests, config and docs; baseline generated from the first full run; pre-commit hook and CI step; AGENTS.md section; then the refactorings up to 9.5 per part on this branch, ordered by change frequency, each followed by `--update-baseline`. Rollback: remove the hook and the CI step.
