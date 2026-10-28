# Proposal

## Why

On 2026-10-28 touchpad and TrackPoint of the ThinkPad L13 Yoga Gen 2 froze at the same time while the touchscreen kept working. Both sit on one Elan I2C chip (`elan_i2c`), which sent no more interrupts. Reloading `elan_i2c` fixed it. The owner wants this fix as a command in the model tuning.

## What Changes

- The model tuning of the ThinkPad L13 Yoga Gen 2 installs the command `touchpad-reset` in `/usr/local/bin`. It reloads the `elan_i2c` driver and re-runs itself with sudo when not started as root.
- The command is not installed on other hardware and is not a `machine` subcommand.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `hardware-tuning`: the requirement "Model tuning selected by the hardware" adds `touchpad-reset` to the L13 Yoga Gen 2 tuning.

Affected hosts: only hosts that report the model `ThinkPad L13 Yoga Gen 2`.

## Impact

- Ansible: `ansible/roles/thinkpad_l13_yoga_gen2` (new file `files/touchpad-reset`, install task, README).
- Docs: `docs/thinkpad-l13-yoga-gen2.md`.
