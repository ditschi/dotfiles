# Proposal

## Why

The project containers `sde` and `sdx` are the eighth area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- `sde` gives a minimal environment close to what colleagues use.
- `sdx` brings the owner's familiar shell customisations into work containers.
- Bash matters as a fallback because some containers lack zsh or cannot install it.
- The commands are for work only; they are not needed on private machines.

## What Changes

- Describe the confirmed behaviour as baseline requirements: the work-only wrappers, project script precedence, the minimal and extended modes, reuse of containers and the `container` profile inside them.
- Features only: no fixes or improvements are added to the baseline. All points of the record were confirmed, so design.md has no investigations.

## Capabilities

### New Capabilities

- `project-containers`: the `sde` and `sdx` launchers for Docker Compose project containers.

### Modified Capabilities

None.

## Open Questions

None.

## Impact

- Decision records: 0008-devcontainers (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
