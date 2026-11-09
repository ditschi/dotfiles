# Proposal

## Why

`machine update` and `machine apply` ask for the sudo password (or fingerprint) only when Ansible starts, after the environment pull, dotfiles, tools and the zsh check. The owner has to wait at the terminal for that prompt in the middle of the run. The owner wants to learn at the start whether the run needs Ansible and sudo authentication, enter it once, and then let the command run to the end without further input for sudo.

## What Changes

- When `machine update` or `machine apply` will run local Ansible, `machine` decides that first and authenticates sudo (fingerprint or password, as today) before the first step that is slow or asks a question: before the environment pull, dotfile apply and tool install in `update`, and before the bootstrap tool install in `apply`. The permission check for `ansible-playbook` as root (restricted sudo) moves to the same point.
- The rule for "will run Ansible" is the one `machine update` already applies after its steps: Ansible is enabled for the host (`ansible: false` skips it), `--skip-ansible` is not given, and the host config changed, `--system` is given, or a changed system file is relevant to this host. A home-only update shows no sudo prompt.
- Right before Ansible starts, `machine` checks the sudo ticket again. When the steps in between took longer than the ticket lasts, it prompts again at that point instead of failing.
- A typo is not a failure: sudo asks again by itself. If sudo gives up, because of a wrong password in every try or missing sudo permission (including a refusal of `ansible-playbook` as root), `machine` reports which of the two it was at that point. `update` then does everything that needs no root, skips Ansible, and reports the failed Ansible step at the end; `apply` skips Ansible and restores the host config as for any failed Ansible run.
- Unchanged: the automatic (background) update never runs Ansible and never prompts; remote runs (`--limit`) keep `--ask-become-pass`; `--no-become` and runs without a terminal still use `sudo -n` and fail early with the existing message.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `system-provisioning`: sudo authentication and the permission check for local Ansible runs happen before the slow steps of `machine update` and `machine apply`, only when Ansible will run, with a renewed check right before Ansible.

Affected profiles: all hosts that run local Ansible (every host without `ansible: false` that is not a container); in practice the private and work desktops and servers. Containers run as root and are not affected.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/early-sudo` on branch `early-sudo`. The change edits the `machine` CLI (`machine_cli/tools.py`, `machine_cli/updates.py`, `machine_cli/commands.py`), which the host's own `machine update` runs from the live checkout.

## Impact

- `machine_cli/tools.py` (the sudo checks of `local_ansible_prefix` become a callable step), `machine_cli/updates.py` (`_update_steps`: decide and authenticate before `env pull`), `machine_cli/commands.py` (`cmd_apply`: authenticate before the bootstrap tool install).
- Tests: `tests/unit/test_host_profiles.py` and `tests/unit/test_update_and_env.py` (order of sudo prompt and steps, no prompt for home-only updates, early failure).
- Docs: `docs/update.md` (one authentication at the start of the run).
