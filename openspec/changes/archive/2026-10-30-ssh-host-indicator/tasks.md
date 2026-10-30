# Tasks

## 1. Prompt

- [x] 1.1 In `home/prompt/.config/starship.toml`, add `($username$hostname )` in front of `$time` and configure `username` (180 / bold 178) and `hostname` (`ssh_only = true`, `@` prefix, 180). Verify with `starship prompt` with and without `SSH_CONNECTION` for `STARSHIP_SHELL=bash` and `zsh`.
- [x] 1.2 Add `tests/unit/test_starship_prompt.py`: renders the first prompt line for bash and zsh with the repo config and asserts `user@host` in front of the time over SSH and no `user@` locally; skips without Starship. Verify with `pytest tests/unit/test_starship_prompt.py -q`.

## 2. Validation

- [x] 2.1 Run `pre-commit run --files` on the changed paths and `pytest tests/unit/test_starship_prompt.py tests/unit/test_zsh_handoff.py tests/unit/test_command_prefix.py -q` (the prompt tests that read `starship.toml`). Result: pre-commit passes; `test_starship_prompt.py` and `test_zsh_handoff.py` 52 passed. `test_command_prefix.py` has 18 failures (`starship_precmd: command not found` in the Starship bash variants), identical on unchanged `main`, so not caused by this change.
- [x] 2.2 After merging: `ssh` into a host and check the prompt in zsh and bash. Result: the owner confirmed the host is shown.
