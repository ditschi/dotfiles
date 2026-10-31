# Proposal

## Why

`~/.ssh/config` is maintained by hand on every host. Entries drift apart and go stale, for example the hosts that still pointed at port 5115 after `sshd_home` moved sshd back to port 22. The client configuration should be rolled out automatically, the same on every host of a context.

Home hosts are reached directly in the home network and through reverse tunnels on the jump host Oracle from outside. Tailscale is not reliable enough to depend on (often logged out, connections drop), so it can only be an optional route. Today this needs separate `jump-*` aliases; the host should instead be reachable under one name, with the route chosen automatically.

New hosts, both home hosts and work hosts such as CI agents, and their host keys should be added through a guided, interactive way instead of by editing files on each host.

## What Changes

- A versioned base config `home/core/.ssh/config` is linked to `~/.ssh/config`. It includes the host-only file `~/.ssh/config.local` first, then the generated files in `~/.ssh/config.d/`, and sets shared defaults under `Host *` (keep-alive, connection sharing, `IdentitiesOnly`, readable `known_hosts`, managed known-hosts file).
- The host list of each context lives as ready `ssh_config` text in a Bitwarden secure note (`ssh/home/config`, `ssh/work/config`). `machine setup`, the manual `machine update` and the new `machine ssh pull` write it to `~/.ssh/config.d/20-home` or `20-work`. No addresses, users, ports or other network details go into the public repository.
- Host blocks that were added or changed locally in the generated file are detected and offered with numbered choices (add to Bitwarden, move to `config.local`, remove, skip), like local-only keys in env files.
- A new script `ssh-route`, used as `ProxyCommand`, tries the routes of a home host in order: home network, Tailscale, jump host. The home network is learned from the host key of the target, not configured; a newly learned home gateway is reported in `machine attention`.
- Public sshd host keys of home hosts are versioned in `machine/ssh_host_keys/<alias>.pub`. Hosts with dotfiles write their own key; devices without dotfiles are added with `machine ssh known-hosts add`. Every host generates `~/.ssh/known_hosts.d/home` from these files, also in the background update.
- The manual `machine update` also checks the host's user public key in `machine/ssh_keys/` and its host key in `machine/ssh_host_keys/` against the local keys, writes missing or different files and reports key files that are not pushed yet in `machine attention`.
- New commands `machine ssh add`, `machine ssh edit`, `machine ssh remove` and `machine ssh pull`; `machine setup` offers to add the host itself to the host list of its context.
- The existing `~/.ssh/config` is backed up once and replaced by the link.

## Capabilities

### New Capabilities

- `ssh-client-config`: layers of the SSH client configuration (base, host list from Bitwarden, host-only file), detection of local host blocks, and the commands to add, edit, remove and pull hosts.
- `ssh-route`: choosing the route to a home host (home network, Tailscale, jump host) and learning the home network.
- `ssh-known-hosts`: public sshd host keys of home hosts in the repository and the generated known-hosts file.

### Modified Capabilities

- `ssh-host-keys`: the manual update also checks the user public key in the repository against the selected local key; the repository file holds only the selected key.
- `update-flow`: `machine attention` lists the new SSH items (local host blocks, key files not pushed yet, newly learned home gateway).
- `work-private-separation`: the separation also covers the SSH host list (`ssh/home/config` or `ssh/work/config`) and managed host keys and routes, which are only used for `private`.

## Impact

All profiles with the `core` dotfile group get the linked base config. Hosts with the context `private` get the home host list, `ssh-route` and the managed known-hosts file; hosts with the context `work` get the work host list only. Containers without a context get the base config without a host list.

Affected code: `home/core/.ssh/config`, `home/core/.local/bin/ssh-route`, `machine/ssh_host_keys/`, `machine_cli/ssh_keys.py` and a new SSH client module in `machine_cli/`, `machine_cli/attention.py`, `machine_cli/updates.py`, the setup flow in `machine_cli/commands.py`, and unit tests. Bitwarden gets two new secure notes; existing items are not changed. No Ansible role changes; `sshd_home` and `authorized_keys` stay as they are.

Made in the worktree `.worktrees/ssh-client-config`, because `home/core/.ssh/config` and `ssh-route` are linked into `$HOME` and `machine_cli` is run directly from the main clone.
