# Proposal

## Why

Machine profiles and the work/private separation are the fourth area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- Work and private hosts share ordinary shell and Git workflows, while profiles and environment groups keep work-specific tools and secrets apart.
- The repository is shareable: secrets and sensitive work details are not committed. A common setup is also usable on private machines for work repositories.

## What Changes

- Describe the confirmed behaviour as baseline requirements: one profile per host, the default profile choice on setup, work detection in the shell, work modules linked and loaded only for work, and the separation of Git identity, Bitwarden groups and SSH key class.
- Unclear points and ideas stay out of the specs and become investigations in design.md: the order of the default profile checks, misclassification of hosts as `container`, `WORK_SETUP` in dev containers, extending the group pattern from environment files to other places, and the boundary between profile and feature.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `machine-profiles`: profiles, their defaults, how the default is chosen, and the per-host files.
- `work-private-separation`: how work-specific behaviour, secrets, Git identity and SSH keys are kept apart from private ones.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0004-work-private-separation (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
