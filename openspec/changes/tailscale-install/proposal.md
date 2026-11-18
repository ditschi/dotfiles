# Proposal

## Why

Selecting the feature `tailscale` installs nothing today: the feature has no apt package entry and no Ansible role, and `machine setup` only offers `sudo tailscale up` when the binary already exists. Its help text ("Tailscale package (+ optional login)") and the setup log line ("package install via ansible") promise an install that never happens. The owner wants the feature to install Tailscale, the same way on every host.

## What Changes

- New Ansible role `tailscale`, run when `tailscale` is in `machine_features`: it adds Tailscale's official apt repository (`pkgs.tailscale.com/stable`) with a pinned signing key and installs the package `tailscale`.
- A host with the Tailscale snap gets no package next to it and a hint; the ThinkPad L13 is moved from the snap to the package once by hand, keeping its tailnet identity, so every host ends up with the same setup (owner decision, 2026-11-18).
- Hosts whose distribution or release the repository does not serve get a warning instead of a failure.
- `machine setup` no longer claims that Ansible installs Tailscale when the binary is missing; it says that Tailscale is not installed and how to log in later.
- `netmaster` and `homeserver` select the feature.
- Bash and Zsh completion for `tailscale` through the existing cached completion helpers.
- Docs (`docs/features.md`, role README) describe the feature and how to undo it.

## Capabilities

### New Capabilities
- `tailscale`: installing Tailscale for the feature `tailscale` and the login offer after setup.

### Modified Capabilities
- None. `feature-selection` (where `tailscale` is offered) and `bootstrap` (login offered after Ansible) keep their requirements.

## Impact

- Profiles: private desktops and servers that select `tailscale` (today `ditschi-ThinkPad-L13-Yoga-Gen-2`, `contabo`, `privatecloud`; `netmaster` and `homeserver` are added). Work hosts and containers are unaffected, the feature is excluded there.
- Code: `ansible/roles/tailscale/` (new), `ansible/workstation.yml`, `machine_cli/ssh_keys.py`, `home/core/.shell/zsh/plugins.zsh`, `home/core/.shell/bash/tools.bash`, tests under `tests/unit/`, `docs/features.md`.
- New external dependency: the apt repository `pkgs.tailscale.com` and its signing key.
- Made in the worktree `$(machine repo)/.worktrees/tailscale-install`, because the shell completion files are live dotfiles and the Ansible role changes what `machine update` does on the host.
