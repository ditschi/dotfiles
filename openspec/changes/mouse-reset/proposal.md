# Proposal

## Why

The command `touchpad-reset` (change `2026-10-28-touchpad-reset`) also resets the TrackPoint, which the owner mainly uses. The owner wants it named `mouse-reset`.

## What Changes

- The L13 Yoga Gen 2 model tuning installs the command as `/usr/local/bin/mouse-reset` instead of `/usr/local/bin/touchpad-reset`. What it does is unchanged.
- `machine apply` removes an installed `/usr/local/bin/touchpad-reset`. No alias for the old name is kept.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `hardware-tuning`: in the requirement "Model tuning selected by the hardware", the command is named `mouse-reset`.

Affected hosts: only hosts that report the model `ThinkPad L13 Yoga Gen 2`.

## Where

Worktree `.worktrees/mouse-reset`, because the change touches `ansible/`, which changes what `machine apply` installs on the host.

## Impact

- Ansible: `ansible/roles/thinkpad_l13_yoga_gen2` (file renamed to `files/mouse-reset`, install task, removal of the old file, README).
- Docs: `docs/thinkpad-l13-yoga-gen2.md`.
