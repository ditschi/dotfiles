# Proposal

## Why

A host that was never bootstrapped for the mise layout (no `mise`, no `~/.config/mise/config.local.toml`; for example one still on the earlier chezmoi layout) silently skipped the converge step in `machine update`, which then reported "update finished". The dotfile links were never created, and the old `~/.zshrc` link stayed dangling, so zsh started its new-user wizard.

## What Changes

- When the converge step cannot run because the host is not set up, `machine update` warns, names `<checkout>/bootstrap` and sets the update state to needs-attention instead of finishing silently.
- In an interactive terminal it additionally asks whether to run `bootstrap` now and runs it on yes. Without a terminal it only warns; `machine update --auto` never runs bootstrap.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `update-flow`: the converge step reports a host that is not set up and offers the bootstrap.

Affected profiles: all.

## Impact

- `machine_cli/updates.py`, `tests/unit/test_update_and_env.py`.
