## 1. State

- [ ] 1.1 Define the state file (four states, reason, applied revision) and have `dotfiles-update-check-job` write it
- [ ] 1.2 Make `machine status` print the state, the reason and the fix

## 2. Shells

- [ ] 2.1 zsh: prompt segment (p10k) comparing the loaded revision with the applied one without forking
- [ ] 2.2 bash: set one variable in `PROMPT_COMMAND` and show it with a Starship `env_var` module
- [ ] 2.3 Refresh the indicator after each command via an mtime check with no fork; measure the per-prompt cost and fall back to start-only evaluation if it is not negligible
- [ ] 2.4 Print the one-line message at shell start for needs-attention only; remove the generic hint from `dot_zshrc` and `dot_bashrc`
- [ ] 2.5 Decide and implement the indicator for `rpi-zero`, `container` and bash without Starship

## 3. Validation

- [ ] 3.1 Unit tests for the states in both shells (extend `tests/unit/test_zsh_handoff.py` and `test_update_and_env.py`)
- [ ] 3.2 Update the Readme
- [ ] 3.3 `pre-commit run --all-files` and `pytest tests/unit -q`
