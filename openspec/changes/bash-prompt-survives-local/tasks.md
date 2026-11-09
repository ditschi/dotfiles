# Tasks

## 1. Restore the hook after the local file

- [x] 1.1 Add the repair function to `home/core/.shell/bash/prompt.bash` and call it in `home/core/.bashrc` right after `~/.bashrc-local` is sourced. Verify: new unit tests in `tests/unit/test_zsh_handoff.py` (local file replaces `PROMPT_COMMAND`, replaces `PS1`, leaves it alone with no double wrap, and Starship missing) pass with `pytest tests/unit/test_zsh_handoff.py -q`.
- [x] 1.2 Extend `test_shells_start_cleanly` in `tests/integration/test_profile_containers.py` with a `~/.bashrc-local` that contains the Ansible "update colors" block. Verify: the Docker profile tests pass (see Readme "Tests").
- [x] 1.3 Update the note on the host-only extension point in `docs/shell.md`. Verify: the text states that the Starship prompt is restored after the local file.

## 2. Validation

- [x] 2.1 Run `pytest tests/unit -q`, because `.bashrc` is shared by every bash session, then `pre-commit run --files <changed paths>` and `openspec validate bash-prompt-survives-local --strict`. Verify: all exit 0.
- [x] 2.2 Check on the work host that `bash -i` shows the Starship prompt with the real `~/.bashrc-local`. Verify: the prompt shows the Starship layout and `PROMPT_COMMAND` equals `starship_precmd`.
