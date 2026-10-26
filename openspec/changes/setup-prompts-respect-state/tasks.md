# Tasks

## 1. Prompts

- [x] 1.1 Replace the number prompt in `system.choose_many` by an arrow/space checklist on a terminal, keeping the number prompt as fallback. Verify a unit test and a run in a pty.
- [x] 1.2 In `setup_bitwarden`, load `~/.env.local` and return early when the session is valid. Verify a unit test that no prompt is shown.

## 2. Checks

- [x] 2.1 Run `pre-commit run --all-files` and `pytest tests/unit -q`. Verify all pass.
