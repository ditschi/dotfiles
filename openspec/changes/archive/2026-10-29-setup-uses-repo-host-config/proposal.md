# Proposal

## Why

A host config in the repository (`machine/hosts/<hostname>.yml`) states which features a host has and who may SSH into it. The first `machine setup` on a host takes context and device from it, but it ignores the features and `ssh_allow_from`. It preselects the defaults and then writes them back to the repository. A feature removed on purpose, such as `monitoring` on `homeserver` and `netmaster` where k3s runs Telegraf, comes back, and the allowed SSH hosts are lost.

## What Changes

- When no applied host config exists, `machine setup` preselects the features of the host's repository config, if the context and device chosen in setup match it. Otherwise it uses the defaults, as before.
- In the same case, `machine setup` offers the `ssh_allow_from` entries of the repository config as the current selection. Without a terminal it keeps them.
- `machine/hosts/homeserver.yml` and `machine/hosts/netmaster.yml` drop `monitoring`. On both hosts, Telegraf runs in k3s (DaemonSet `monitoring/telegraf-agent`).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `feature-selection`: "Menu shows only allowed features". Features listed in the host's repository config count as features the host already has.
- `machine-profiles`: new requirement. A first setup keeps the `ssh_allow_from` of the repository config.

Profiles affected: every host with a repository host config and no applied host config (fresh setup), private and work.

## Impact

- `machine_cli/commands.py` (`cmd_setup`).
- `tests/unit/test_host_profiles.py`.
- `machine/hosts/homeserver.yml`, `machine/hosts/netmaster.yml`.
