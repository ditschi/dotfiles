# Git Work Owner Suffix

## Why

GitHub owners ending in `_bosch`, including `dci2lr_bosch`, must select the work
Git identity and credentials automatically from the remote URL.

## What Changes

- Extend the shared owner rules to HTTPS and SSH GitHub remotes with `*_bosch` owners.
- Keep existing work-owner prefixes and private-owner behavior unchanged.
- Match the owner, not the repository name or an owner merely containing `_bosch`.

## Capabilities

### Modified Capabilities

- `git-config`: work identity selection by GitHub owner suffix.

## Impact

All profiles using the shared Git configuration. Update the shared config,
owner-selection unit tests, and Git documentation; no secret values change.
