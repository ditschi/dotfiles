# Proposal

## Why

`machine setup` and `machine update` shall apply their steps in the same order. A new host shall get a good shell quickly: the dotfile groups and the user-space tools from `mise` come before Ansible, so the shell environment is complete before Ansible starts. Ansible can then keep running while the user already works in another terminal with the full shell.

The env pull comes first, before `mise`, so that its questions about local-only keys are asked before the long tool install and not in the middle of the run.

A failing step shall not hold back the steps that do not need it: setup and a manual update try every independent step and report one overall result at the end. Otherwise a failing `bw sync` at the start would now also keep the dotfile groups, the tools and Ansible from being applied.

Today `machine setup` runs Ansible first and applies the dotfile groups, the tools and the env files only afterwards; `machine update` applies the dotfile groups and tools first, then the env files, then Ansible.

## What Changes

- `machine setup` and `machine update` both run in this order: env pull, dotfile groups (`mise dot apply`), user-space tools (`mise install` and the feature steps that follow it), then Ansible.
- In `machine setup`, after the tools and before Ansible, a line says that the shell is ready in a new terminal while Ansible continues.
- In `machine setup`, the steps that depend on Ansible or should not start during it stay after Ansible: the SSH host key, the Tailscale login (its package comes from Ansible) and enabling the update and disk-check timers.
- `machine setup` and a manual `machine update` run every step even after an earlier one failed, unless the step needs the failed one (the tool install and the zsh health check need the dotfile apply). At the end they list each failed or skipped step with its reason and exit with a non-zero status; update also sets the state to needs-attention naming the steps. Failures while updating the checkout and Ctrl-C still stop at once. The restore after a failed Ansible apply is unchanged.
- `--skip-dotfiles`, `--skip-ansible` and `ansible: false` keep their meaning. The background update (`machine update --auto`) does not pull env files and is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `bootstrap`: adds the order in which `machine setup` applies the env files, the shell environment and Ansible, and that setup tries every independent step and reports all failures at the end.
- `update-flow`: adds that `machine update` pulls the env files before it applies the dotfile groups and the tools, and that a manual update tries every independent apply step and ends with one result listing every failed step. The background job keeps its revert on the first failure.

Profiles: all contexts and devices. Containers are unaffected in effect, because they have no context (no env pull) and Ansible does not run there.

## Impact

- Code: `machine_cli/commands.py` (`cmd_setup`), `machine_cli/updates.py` (`_update_locked`), possibly a small shared helper for running a step and collecting its result.
- Tests: `tests/unit/test_host_profiles.py` (setup order), `tests/unit/test_update_and_env.py` (update order).
- No change to `machine apply`, the background update, Ansible or the `mise` configuration.
- Where: worktree `.worktrees/setup-tools-before-ansible` on branch `setup-tools-before-ansible`, because the change touches `machine_cli/`, which the host's `machine` command reads from the main clone.
