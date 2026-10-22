## Why

Updates should not depend on the user remembering to run `machine update`. Changes that only touch home files are safe to apply in the background; changes that need the system step or manual checking must not be.

## What Changes

- The background job applies updates automatically when the checkout has no local changes (after the resolvers) and only home files changed: fast-forward pull plus chezmoi apply.
- System or host-profile changes are not applied in the background; they are shown by the indicator from `update-state-and-hint`.
- When automatic update is not possible, the state is needs-attention with the reason.
- After an automatic update the state says the shell needs a reload.

## Capabilities

### Modified Capabilities
- `update-flow`: "Explicit update" now allows the automatic update of home-only changes; system changes stay explicit.

Profiles: all profiles that run the update-check timer.

## Impact

`home/dot_local/bin/executable_dotfiles-update-check-job`, systemd timer and service units, `home/dot_local/lib/machine_cli/commands.py`, `tests/unit`, Readme.

Depends on `update-classification` and `update-state-and-hint`.
