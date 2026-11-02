# Tasks

## 1. Inventory CLI completions

- [x] 1.1 Audit command-line tools declared in core and feature mise fragments; verify native Bash/Zsh generator syntax, configured-provider coverage and shell-framework prerequisites, including Copilot CLI, Zellij, GitHub CLI, OpenCode, uv and mise, and document upstream-only static completions not included in this change.

## 2. Add shell completions

- [x] 2.1 Add cache-aware Zsh completion generation and registration for supported tools, retaining configured provider completions; verify registration occurs after `compinit` and before `fzf-tab`, optional tools are silent when absent, and `pytest tests/unit/test_zsh_handoff.py -q` passes.
- [x] 2.2 Add cache-aware Bash completion generation for supported tools while retaining configured provider completions independently of the optional system `bash-completion` package, except GitHub CLI and Git LFS which must be gated on their required helper; verify startup with and without the package and `pytest tests/unit/test_zsh_handoff.py -q` passes.

## 3. Document and validate

- [x] 3.1 Add the future-tool completion rule to `openspec/config.yaml` and update shell documentation with completion registration locations and unsupported cases; verify `openspec instructions proposal --change shell-tool-completions --json` includes the rule and documented paths match the loaders.
- [x] 3.2 Run `pytest tests/unit/test_zsh_handoff.py -q` and `pytest tests/integration/test_profile_containers.py -q`; record results and explain how the focused startup tests cover both shells and profile setup.
  - 2026-11-02: `test_zsh_handoff.py` 50 passed; `test_profile_containers.py` (via `uvx nox -s docker`) 11 passed. Full unit suite 869 passed after making two tests independent of the caller environment (exported `ZSH`, umask 002).
  - Coverage: `test_zsh_handoff.py` starts real zsh and bash with temporary homes (zsh completion registration offline and after `compinit`, Bash native completion with and without `bash-completion`, gh/Git LFS helper gating, Bash-to-zsh handoff); `test_profile_containers.py` installs each host profile in Docker and checks the dotfile links and that both shells start cleanly.
- [x] 3.3 Run `pre-commit run --files` for every changed path, including new files, and record the result.
