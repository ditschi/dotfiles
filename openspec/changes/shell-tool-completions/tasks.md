# Tasks

## 1. Inventory CLI completions

- [x] 1.1 Audit command-line tools declared in core and feature mise fragments; verify native Bash/Zsh generator syntax, configured-provider coverage and shell-framework prerequisites, including Copilot CLI, Zellij, GitHub CLI, OpenCode, uv and mise, and document upstream-only static completions not included in this change.

## 2. Add shell completions

- [x] 2.1 Add cache-aware Zsh completion generation and registration for supported tools, retaining configured provider completions; verify registration occurs after `compinit` and before `fzf-tab`, optional tools are silent when absent, and `pytest tests/unit/test_zsh_handoff.py -q` passes.
- [x] 2.2 Add cache-aware Bash completion generation for supported tools while retaining configured provider completions independently of the optional system `bash-completion` package, except GitHub CLI and Git LFS which must be gated on their required helper; verify startup with and without the package and `pytest tests/unit/test_zsh_handoff.py -q` passes.

## 3. Document and validate

- [x] 3.1 Add the future-tool completion rule to `openspec/config.yaml` and update shell documentation with completion registration locations and unsupported cases; verify `openspec instructions proposal --change shell-tool-completions --json` includes the rule and documented paths match the loaders.
- [ ] 3.2 Run `pytest tests/unit/test_zsh_handoff.py -q` and `pytest tests/integration/test_profile_containers.py -q`; record results and explain how the focused startup tests cover both shells and profile setup.
- [x] 3.3 Run `pre-commit run --files` for every changed path, including new files, and record the result.
