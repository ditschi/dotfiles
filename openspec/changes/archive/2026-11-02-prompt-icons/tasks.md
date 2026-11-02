# Tasks

## 1. Prompt configuration

- [x] 1.1 Update `home/prompt/.config/starship.toml`: git icon and coloured status counts, `💻 ssh` marker on the second line, Python segment only with an active virtualenv, one meaning per colour; verify with `pytest tests/unit/test_starship_prompt.py -q` (new tests for the git segment, the SSH marker on line 2 and the virtualenv-only Python segment).
  - 2026-11-02: 6 passed; the owner previewed the result in Ddterm and the VS Code terminal with `STARSHIP_CONFIG` pointing at the worktree.
- [x] 1.2 Run `pre-commit run --files home/prompt/.config/starship.toml tests/unit/test_starship_prompt.py openspec/changes/prompt-icons/**` and `openspec validate --strict --type spec --specs`.

## Workflow follow-up

- Archive inside the worktree, squash the branch into one commit, merge into main and push (owner approved).
