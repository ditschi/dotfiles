# Proposal

## Why

The update mechanism is the seventh area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- The background check keeps shell startup fast while still telling the user when an update is available.
- Updates stay explicit for now. Automatic updates are planned as soon as possible, but they must never overwrite local work.
- Updating an existing machine covers both the dotfiles and the applicable Ansible-managed system and tool state.
- Conflicts and uncommitted changes are detected and explained, never silently discarded.

## What Changes

- Describe the confirmed behaviour as baseline requirements: the shell hint, `machine update` with its safety checks, and the shell helpers.
- Points the owner marked unclear and goals stay out of the specs and become investigations in design.md: the systemd timer, when Ansible runs, restore after a failed apply, removal of the layout migration offer, reloading the shell after an update, syncing local changes, automatic rollout, and remote updates.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `update-flow`: how the user learns about updates and how `machine update` applies them.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0007-update-mechanism (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
