# Proposal

## Why

Git configuration is the sixth area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- Repositories are cloned under different roots on different machines, so paths are not a reliable way to tell work from private; the owner of the remote decides the identity.
- Shared aliases and defaults should sync with the dotfiles.

## What Changes

- Describe the confirmed behaviour as baseline requirements: the shared `~/.gitconfig`, the host-local `~/.gitconfig.local`, identity by remote owner, per-repository overrides, and keeping host-only keys out of the shared file.
- Points the owner marked unclear stay out of the specs and become investigations in design.md: the credential helper layout, the local `store` helper, `user.useConfigOnly`, and suspected legacy settings.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `git-config`: the layers of Git configuration, identity selection and the split between shared and host-only settings.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0006-git-config (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
