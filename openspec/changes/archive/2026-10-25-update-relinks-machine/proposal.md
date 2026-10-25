# Proposal

## Why

A host on the earlier layout has `~/.local/bin/machine` as a copied script that imports its modules from the checkout. As soon as the checkout is switched to a branch without those modules, `machine` fails to start (`ImportError`), and `machine update` cannot repair it: only bootstrap creates the symlink to the CLI in the checkout. Running the new CLI from the checkout (`~/dotfiles/machine_cli/machine update`) applied the dotfiles but left the broken entry point in place (found with `machine testenv`).

## What Changes

- Every dotfile apply, as part of `machine setup` and of the converge step of every `machine update`, makes `~/.local/bin/machine` a symlink to `machine_cli/machine` of the running checkout, replacing a regular file or a link elsewhere.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `update-flow`: the converge step also repairs the `machine` entry point.

Affected profiles: all.

## Impact

- `machine_cli/dotfiles.py`, `tests/unit/test_dotfiles.py`.
