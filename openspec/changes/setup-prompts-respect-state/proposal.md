# Proposal

## Why

Found while bootstrapping a host: (1) the feature menu only accepted numbers, although a checklist with arrow keys and space is the expected way to select; (2) `machine setup` asked "Configure Bitwarden and log in now?" although a valid `BW_SESSION` was already saved in `~/.env.local`.

## What Changes

- In a terminal the feature (and SSH host) selection is a checklist: arrow keys (or `j`/`k`) move, space toggles, `a`/`n` select all/none, Enter confirms. Where keys cannot be read, the number-toggle prompt is used as before.
- `machine setup` reads `~/.env.local` first and does not ask about Bitwarden when the saved session is still valid.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `feature-selection`: interactive selection by checklist.
- `secret-tools`: a valid saved session suppresses the Bitwarden setup prompts.

Affected profiles: all.

## Impact

- `machine_cli/system.py`, `machine_cli/bw_client.py`, `tests/unit/`.
