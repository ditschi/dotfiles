# Proposal

## Why

On hosts whose home is reachable by two paths, VS Code's Copilot CLI wrapper calls itself recursively; on the work VM ABTVL421 this exhausted memory and needed a reboot.

## What Changes

- Shell startup rewrites the `PATH` entry of VS Code's Copilot CLI wrapper directory (`…/github.copilot-chat/copilotCli`) to its canonical path. The wrapper's own `PATH` filter then matches, and `copilot` resolves to the real CLI instead of the wrapper. Other `PATH` entries and their order stay unchanged.
- `machine status` shows an informational note in the host row when `$HOME` differs from its canonical path, so hosts with this layout are visible.
- An upstream issue for `microsoft/vscode-copilot-chat` was drafted, asking the shim to compare canonical paths and to guard against recursion; the owner decided not to file it in this change.

## Capabilities

### New Capabilities
- `vscode-terminal-path`: how the dotfiles keep `PATH` entries injected by VS Code into terminals safe on hosts with an aliased home, and how `machine` reports such a home.

### Modified Capabilities

None.

## Impact

Applies to every context and device; it has an effect only where `$HOME` is reachable through a symlink or bind mount (target case: ABTVL421, home under `/mnt/data`). On other hosts the canonical path equals the existing entry, so nothing changes.

- `home/core/.shell/common/environment.sh` (loaded by Bash, zsh and `git-credential-env`).
- `machine_cli/commands.py` (`cmd_status` host row).
- Tests in `tests/unit/`.
- No Ansible, packages, secrets or new tools.
