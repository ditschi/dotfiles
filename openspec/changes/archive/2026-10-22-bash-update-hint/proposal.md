## Why

The backlog listed "update hint in bash" as missing. `home/dot_bashrc` already prints the hint (since the chezmoi migration), but the `update-flow` spec only names zsh and no test covers bash. The backlog entry is stale.

## What Changes

- The `update-flow` spec requires the hint in interactive bash as well as zsh.
- A unit test covers the bash hint.
- The backlog entry is removed.
- No code change in `dot_bashrc`.

## Capabilities

### Modified Capabilities
- `update-flow`: "Update hint at shell start" covers bash and zsh.

## Impact

`openspec/specs/update-flow`, `tests/unit/test_zsh_handoff.py` (reuses its `run_bashrc` helper), `openspec/backlog.md`.
