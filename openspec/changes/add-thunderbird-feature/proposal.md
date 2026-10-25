# Proposal

## Why

Private laptops should be able to get Thunderbird together with `thunderbird-cli` (`tb`), a command line client that lets the shell and AI agents read and write mail in the local Thunderbird. `tb` talks to Thunderbird through a bridge daemon (`thunderbird-cli-bridge`) and a Thunderbird extension. The bridge is only useful when the extension can be installed too, so the two are installed together or not at all.

## What Changes

- New feature `thunderbird`, on by default for `home-laptop` only.
- Ansible installs the `thunderbird` package. On Ubuntu that is the snap, through the transitional deb. It also adds the signed extension "Thunderbird AI Bridge" (`thunderbird-ai@extension`) through a system policy in `/etc/thunderbird/policies/policies.json` (`ExtensionSettings`). Thunderbird installs the extension on its next start; the Ubuntu snap reads `/etc/thunderbird` through its `system-files` plug. Other policies already in that file are kept.
- The feature selects a new dotfile group `thunderbird` with a mise fragment for `npm:thunderbird-cli` and `npm:thunderbird-cli-bridge`. The CLI and the bridge are installed only together with the feature that installs the extension.

## Capabilities

### New Capabilities
- `thunderbird-cli`: the `thunderbird` feature: Thunderbird, the extension policy and the `tb` CLI with its bridge.

### Modified Capabilities
- `system-provisioning`: the local roles include `thunderbird`.

Affected profiles: `home-laptop` by default. Other profiles can select the feature. It needs root for the package and the policy, so it does not fit work machines.

## Impact

- `machine_cli/core.py` (feature), `machine_cli/dotfiles.py` (group), `mise.toml` (group), `home/thunderbird/.config/mise/conf.d/60-thunderbird.toml`, `home/core/.config/mise/mise.lock` and `locks/`, `ansible/group_vars/all.yml` (package), new role `ansible/roles/thunderbird`, `ansible/workstation.yml`, `ansible/profiles/home-laptop.yml`, tests, Readme.
- The bridge daemon is started by hand (`tb-bridge &`); no service is installed.
