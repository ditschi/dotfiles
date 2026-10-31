# Proposal

## Why

On the aarch64 host `netmaster` (Raspberry Pi, Debian 13), `machine env pull` offers to install the Bitwarden CLI and then stops with "no Bitwarden CLI build for aarch64". The host therefore cannot back up its SSH key to Bitwarden automatically, cannot pull its env files and, once `ssh-client-config` lands, cannot pull the SSH host list. The owner wants the Bitwarden CLI installed the same way on every host, Raspberry Pi or laptop, with as little maintenance as possible.

## What Changes

- `bw` comes from `mise` as the tool `bitwarden` (`aqua:bitwarden/clients`, the official Bitwarden release build) in the `core` group, so every host gets it. `mise.lock` pins the version and the checksums for linux-x64 and linux-arm64; an update is a lockfile commit like every other tool.
- **BREAKING** (spec): `bw` is no longer installed to `~/.local/bin`. The custom download, checksum and unzip code in `machine` is removed, together with the version it hard-codes (2024.12.0).
- When `machine` needs `bw` before the dotfiles are linked (early in `machine setup`) or finds it missing (`machine env pull`), it installs the pinned `bitwarden` from the repository's `core` mise configuration instead of downloading it itself.
- `machine setup` and `machine update` remove an old `~/.local/bin/bw` once `mise` provides `bw`, and log it, so the old binary cannot shadow the pinned one.
- `bw` completion is enabled in zsh (`bw completion --shell zsh`). `bw` has no Bash completion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `secret-tools`: the Bitwarden CLI comes from `mise` on every host and every supported CPU (x86_64, aarch64) instead of a download to `~/.local/bin`; an old `~/.local/bin/bw` is removed.

Profiles: every profile, because the tool goes into the `core` group (also `container` hosts, see design.md Risks). Private and work hosts get the same tool.

## Impact

- Code: `machine_cli/tools.py` (`ensure_bitwarden_cli`, `ensure_bootstrap_tools`), `machine_cli/bw_client.py` (`require_bitwarden`), the setup and update paths that call them, the zsh tool completions.
- Config: `home/core/.config/mise/conf.d/20-tools.toml`, `home/core/.config/mise/mise.lock`.
- Docs: Readme "Secrets / Bitwarden".
- Tests: `tests/unit/test_host_profiles.py` and new unit tests for the install and the old-binary removal.
- Dependencies: the Bitwarden CLI release on GitHub (`bitwarden/clients`, `cli-v*`); it has published an arm64 Linux build since `cli-v2026.3.0`.
- Where the change is made: the existing git worktree `.claude/worktrees/lucid-euclid-47f907`, not the main clone, because the change touches `home/`, `machine_cli/` and the mise configuration that the live main clone serves to the host's shell. The owner chose this worktree over a new one under `.worktrees/`, since the session already runs in it and no worktree is nested.
