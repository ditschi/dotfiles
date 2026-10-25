# Proposal

## Why

Private laptops should be able to get Thunderbird together with `thunderbird-cli` (`tb`), a command line client that lets the shell and AI agents read and write mail in the local Thunderbird. `tb` talks to Thunderbird through a bridge daemon (`thunderbird-cli-bridge`) and a Thunderbird extension. The extension connects without authentication to whatever bridge listens on `127.0.0.1:7701`. On a host with several logged-in users, one user's bridge (and agent) could reach the mail of every Thunderbird that has the extension. Therefore the extension is not installed automatically for everyone; the owner installs it by hand in their own Thunderbird.

## What Changes

- New feature `thunderbird`, on by default for `home-laptop` only.
- Ansible installs the `thunderbird` package (`packages_by_feature`). On Ubuntu that is the snap, through the transitional deb.
- The feature selects a new dotfile group `thunderbird` with a mise fragment for `npm:thunderbird-cli` and `npm:thunderbird-cli-bridge`.
- During the tool install, `machine` downloads the pinned extension XPI, verified by SHA-256, to `downloads/` in the checkout (gitignored) and tells the user how to install it from file.

## Capabilities

### New Capabilities
- `thunderbird-cli`: the `thunderbird` feature: Thunderbird, the `tb` CLI with its bridge, and the extension provided for a manual install.

### Modified Capabilities
- None.

Affected profiles: `home-laptop` by default. Other profiles can select the feature. The package needs root; the CLI, the bridge and the download do not.

## Impact

- `machine_cli/core.py` (feature), `machine_cli/dotfiles.py` (group), `machine_cli/mise_tools.py` (download), `mise.toml` (group), `home/thunderbird/.config/mise/conf.d/60-thunderbird.toml`, `home/core/.config/mise/mise.lock` and `locks/`, `ansible/group_vars/all.yml` (package), `ansible/profiles/home-laptop.yml`, `.gitignore`, tests, Readme.
- The bridge daemon is started by hand (`tb-bridge &`); no service is installed.
