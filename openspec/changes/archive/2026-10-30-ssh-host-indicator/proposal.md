# Proposal

## Why

Before the switch from Powerlevel10k to Starship, zsh showed `user@hostname` when the shell ran over SSH, so a remote shell could be told apart from a local one at a glance. The switch lost this indicator, and bash never had it. Both shells should show it again.

## What Changes

- The shared Starship prompt shows `user@hostname` on the first line, in front of the time, when the shell runs over SSH.
- In a root shell the user name is shown as well, also without SSH, as the p10k context segment did.
- Colours follow the former p10k segment: 180 for a normal user, bold 178 for root.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shell-prompt`: adds the SSH/root context to the first prompt line in zsh and bash.

## Impact

Every context and device that links the shared Starship configuration (all profiles). Only `home/prompt/.config/starship.toml` and a new unit test change; no packages, Ansible or secrets. The plain fallback prompt without Starship is not changed.

Made in the worktree `.worktrees/ssh-host-indicator`, because `starship.toml` is linked into `$HOME` and read by every new shell.
