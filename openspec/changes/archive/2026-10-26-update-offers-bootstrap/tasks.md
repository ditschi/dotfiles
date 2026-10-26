# Tasks

## 1. Update

- [x] 1.1 In `machine update`, when `mise` or `~/.config/mise/config.local.toml` is missing: warn with the bootstrap path, set the state to needs-attention, and in an interactive terminal offer to run `bootstrap`. Verify unit tests for a run without a terminal, a yes and a no.

## 2. Checks

- [x] 2.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `openspec validate update-offers-bootstrap --strict`. Verify all pass.
