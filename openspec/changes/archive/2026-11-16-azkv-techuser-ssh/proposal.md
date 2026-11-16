# Proposal

## Why

The CI agents are reached with technical users (`ci-user-a` for the first group of agents, `ci-user-b` for the second; placeholders for the real user names). Their passwords live in an Azure Key Vault, which is always the current truth, and in Bitwarden, where they are often outdated. Today the password is looked up by hand whenever the SSH key is not yet authorized on an agent. Bitwarden stays in use for the browser (logins, creating tokens for the users), so it has to follow Azure instead of being dropped.

## What Changes

- `ssh` connections to a host that the SSH config resolves to one of the technical users fetch the password from Azure Key Vault with the installed `az` when ssh needs a password, that is, after key authentication failed. All other connections stay unchanged.
- The mapping from technical user to vault and secret is the key `AZKV_TECHUSERS` in the Bitwarden group item `env/groups/work`, so no vault name enters the repository.
- `machine secrets sync` (and a step of the manual `machine update` on hosts that have the mapping) copies the Key Vault password into the existing Bitwarden login item of the same name when both differ. Azure always wins; Bitwarden keeps the old password in its item history.
- A missing or expired `az` login does not stop anything; it becomes an item in `machine attention`.
- No helper installs the SSH key on the agents; `ssh-copy-id` as the technical user works unchanged and is documented.

This change is made in the worktree `$(machine repo)/.worktrees/azkv-techuser-ssh`, because the `ssh` wrapper changes how every `ssh`, `scp`, `rsync` and `git` call on a work host behaves.

## Capabilities

### New Capabilities

- `techuser-ssh-password`: when `ssh` needs a password for a technical user, it is read live from Azure Key Vault; scoping to those users; fallback to the terminal.
- `techuser-password-sync`: `machine secrets sync` keeps the Bitwarden items of the technical users equal to Key Vault.

### Modified Capabilities

None. `env-files` is unchanged: `AZKV_TECHUSERS` is an ordinary key of an existing group item.

## Impact

- New files in the `work` dotfile group: `home/work/.local/bin/ssh` (wrapper) and `home/work/.local/bin/ssh-askpass-azkv`.
- `machine_cli`: a new mixin for the sync, a `secrets` command group in `machine_cli/machine`, a step in the manual update flow, an attention item.
- `docs/ssh.md`, `docs/secrets.md`; new unit tests with fake `ssh`, `az` and `bw`.
- Profiles: `work` only. Private hosts get neither the wrapper nor the sync step.
- Depends on `az` being installed and logged in (provisioned by Ansible, see `system-provisioning`) and on `bw` for the sync.
