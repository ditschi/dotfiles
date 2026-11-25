# Code health

Code health is measured with [ai-health](https://github.com/epatel/ai-health) (MIT, deterministic, no AI needed), modelled on [CodeScene Code Health](https://codescene.io/docs/guides/technical/code-health.html). Score 1-10 per file and per component; the target is 10 (no finding), 9.5 is the minimum on the way there. Agents develop against it; pre-commit and CI keep it from getting worse.

## Commands

```bash
scripts/aihealth delta --config .aihealth.toml                     # changed files (incl. untracked) vs HEAD; exit 1 if worse
scripts/aihealth delta --config .aihealth-tests.toml tests         # the same for the tests component
scripts/aihealth delta --config .aihealth.toml --format json       # JSON, for agents
scripts/aihealth scan . --config .aihealth.toml                    # report: python-cli and shell
scripts/aihealth scan tests --config .aihealth-tests.toml          # report: python-tests
scripts/aihealth scan machine_cli/updates.py --config .aihealth.toml -v   # one file, every finding
uvx nox -s code-health                                             # both scans plus the score of each component
scripts/aihealth_components.py --compare "$(git merge-base origin/main HEAD)" HEAD   # what CI checks
```

`scripts/aihealth` only pins ai-health to a commit (so `uvx` serves it from the cache, also offline after the first run) and passes every argument through. Always give `--config`: `aihealth scan <dir>` otherwise reads `<dir>/.aihealth.toml` and silently falls back to the defaults. `scripts/aihealth_components.py` exists because ai-health has no comparison of component scores between two revisions; it exports both with `git archive`, scans them with the checkout's profiles and splits the JSON by language. A full scan takes about 3 s.

## Components

| Component | Files | Config |
| --- | --- | --- |
| `python-cli` | Python outside `tests/`, `openspec/` and `.claude/skills/` | `.aihealth.toml` |
| `shell` | sh, bash and zsh files outside the same directories, including `home/**/.local/bin` and `home/**/.shell` | `.aihealth.toml` |
| `python-tests` | Python under `tests/` | `.aihealth-tests.toml` |

Not scored:
- Ansible: ansible-lint is its gate (owner decision).
- Python scripts without a file extension (`machine_cli/machine`, `home/core/.local/bin/ssh-route`, `home/ssh-tunnel/.local/bin/ssh-tunnel`, `home/work/.local/bin/work-net`, `ansible/roles/homelab_node/files/homelab-ci`): ai-health does not detect them yet ([epatel/ai-health#3](https://github.com/epatel/ai-health/issues/3)).
- Test-specific smells (large and duplicated assertion blocks): ai-health has none yet.
- `.claude/skills/`: third-party agent skills, pinned in `skills-lock.json`.

## Profile "strict"

`.aihealth.toml` (owner decision 2026-11-23): CodeScene thresholds - cyclomatic complexity > 9, function > 70 lines, > 4 arguments, nesting 4, bumpy road 2 bumps, complex conditional 2 `and`/`or`, file > 600 lines, primitive obsession > 30 % of typed parameters (ai-health counts `str`, numbers, `bool` and the plain containers `dict`/`list`/`tuple`/`set` as primitive) - plus `decay = 8`, `symbol_cap = 4`, `density_loc = 100000` and `delta.tolerance = 0`. File score `10 - 9 x (1 - e^(-P/8))`, P the sum of the weighted findings; component score = mean of the file scores weighted by lines of code.

`.aihealth-tests.toml` repeats the profile and sets the weights of `excess_arguments` (pytest fixtures arrive as arguments), `primitive_obsession` and `low_cohesion` (test classes group cases) to 0. `tests/unit/test_aihealth_config.py` keeps the shared sections of both files equal: change the profile in `.aihealth.toml` and copy it.

## Gate

- pre-commit `aihealth-delta` and `aihealth-delta-tests`: `delta --staged` per component; fails when a staged file gets worse or a new file has a finding.
- CI job `code-health`: `delta` against the merge base with `origin/main`, not its tip, so a branch behind `main` is not charged with newer changes there, the component comparison of merge base and head (a component may drop at most 0.01, which absorbs deleting a healthy file), and the full scan as a report (`delta` does not see duplication across files). The uv cache and `~/.cache/tree-sitter-language-pack` (about 30 MB of grammars) are cached.
- Suppressions are file-wide only: `# aihealth: disable=<smell>[, <smell>] -- <reason>`. Without ` -- ` ai-health takes the reason as part of the smell name and silently ignores the suppression; the pygrep hook `aihealth-suppression-reason` rejects suppressions without ` -- ` and a reason of at least ten characters.
- Linting is separate: ruff (format and pycodestyle/pyflakes rules), shellcheck, shfmt, ansible-lint. Their structure rules stay off; each smell has one source, ai-health.

## Steckbrief Code Health

Profile for comparing this approach with the other repositories; the headings are fixed.

### 1. Messumfang

Three components with their own score and the target 10 (minimum 9.5): `python-cli` (all Python outside `tests/`, `openspec/` and `.claude/skills/`), `python-tests` (`tests/`) and `shell` (sh, bash, zsh, including dotfiles in hidden directories, which ai-health lists through `git ls-files`). Not scored: Ansible (ansible-lint only, owner decision), Python scripts without an extension (documented gap, epatel/ai-health#3); third-party skills in `.claude/skills/`. An overall score is not used for the gate; a large Python share would hide the shell component.

### 2. Tools und Versionen, je Sprache

- Python and shell: ai-health v0.4.0, pinned to commit `033d1867fe514867d944d9387ee72db0188eed47` in `scripts/aihealth`, run with `uvx` (tree-sitter-language-pack for parsing).
- Lint: ruff 0.17.6 (replaces black and flake8), shellcheck 0.11, shfmt 3.10, ansible-lint.
- Before ai-health, this change built an own checker on the Python standard library (`code_health/`, `ast`/`tokenize`, a line-based shell parser, PyYAML for Ansible), cross-checked with radon 6.0.1 (cyclomatic complexity equal for 533 of 537 functions) and complexipy 9.0.0 (cognitive complexity equal for 526 of 537). It found the same hotspots and was removed once ai-health was in place, following the owner's rule of no own logic where a tool exists. Checked and not used: lizard (no shell), ruff's structure rules (pass/fail without values), jscpd (Node).

### 3. Abgebildete Smells

ai-health covers complex method, large method, brain method, excess arguments, primitive obsession, code duplication (also across files in `scan`), deep nesting, bumpy road, complex conditional, cognitive complexity, large file and low cohesion (LCOM4). Not covered: brain class/god class and many functions per module as separate smells, large and duplicated assertion blocks (no test smells for Python yet), constructor over-injection (constructors count like any function). Switched off for `python-tests`: excess arguments, primitive obsession, low cohesion.

### 4. Schwellen, Gewichte und Score-Formel

See [Profile "strict"](#profile-strict). ai-health's default weights (brain method 2.0, large file 1.5, complex method 0.75, ...); severity = value / threshold, at most 3; per symbol the penalties are capped at 4; file score `10 - 9 x (1 - e^(-P/8))`, no density relief for large files.

### 5. Bedienung

`scripts/aihealth delta --config <component config>` (text or `--format json`), `scripts/aihealth scan <dir> --config <component config>`, `uvx nox -s code-health` (the repository's task runner is nox). `delta` checks changed files only (working tree, `--staged`, or `--base`/`--head`). About 3 s for a full scan, well under a second for a small delta after the first run.

### 6. Gate

pre-commit hooks `aihealth-delta` and `aihealth-delta-tests` (`delta --staged` per component, tolerance 0, new files without findings) and the CI job `code-health` (delta against the merge base, component comparison with tolerance 0.01, report). No stored baseline: the base revision is the ratchet. Suppressions file-wide with a reason, enforced by a pygrep hook.

### 7. Ergebnis

Before (ai-health with the final strict profile on `main` 0a3d695, measured 2026-11-24 with `scripts/aihealth_components.py 0a3d695`): `python-cli` 3.97, `python-tests` 6.30, `shell` 8.89. Worst files: `tests/unit/test_update_and_env.py` 1.28, `machine_cli/ssh_client.py` 1.49, `machine_cli/netrc_sync.py` 1.52, `tests/unit/test_host_profiles.py` 1.62, `machine_cli/env_push.py` 1.94. The own checker measured the same hotspots (`python-cli` 3.76, `python-tests` 6.49, `shell` 8.10, `ansible` 8.65).

After: added once the refactorings are done.

### 8. Skills

Searched with `npx skills find` (python, refactoring, testing, tdd, debugging, git, code review, documentation, shell, ansible, ci, and more); every adopted SKILL.md was read before. Adopted, project-local under `.claude/skills/` and pinned in `skills-lock.json` (pre-commit leaves them untouched): `wondelai/skills@refactoring-patterns`, `wshobson/agents@python-testing-patterns`, `obra/superpowers@systematic-debugging`, `obra/superpowers@verification-before-completion`, `obra/superpowers@receiving-code-review`, `mattpocock/skills@writing-for-agents`, `github/awesome-copilot@github-actions-hardening`. Rejected, among others: `codehealth-mcp` (paid CodeScene token), `obra/superpowers@brainstorming`, `writing-plans` and `mattpocock@to-spec` (compete with OpenSpec), `obra/superpowers@using-git-worktrees` (ignores this repository's worktree rule), `getsentry@agents-md` (prescribes `Co-Authored-By`), `test-driven-development` and `mattpocock@tdd` (dogmatic or blocking autonomous work), `wshobson@bash-defensive-patterns` (a blanket `set -Eeuo pipefail` changes behaviour).

### 9. Erfahrungen

Added once the refactorings are done.
