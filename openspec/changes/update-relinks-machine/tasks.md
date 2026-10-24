# Tasks

## 1. Entry point

- [x] 1.1 Link `~/.local/bin/machine` to `machine_cli/machine` of the running checkout at the end of every dotfile apply, atomically, replacing a regular file or another link. Verify unit tests for a copied entry point, a link elsewhere and a second run.
- [ ] 1.2 In `machine testenv` on a host on the earlier layout: discard local changes, switch to the branch, run `~/dotfiles/machine_cli/machine update`. Verify `machine` starts afterwards.

## 2. Checks

- [ ] 2.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `openspec validate update-relinks-machine --strict`. Verify all pass.
