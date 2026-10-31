# Proposal

## Why

`machine update` and the background job update the checkout and then run the remaining steps (env pull, dotfile apply, tool install, health checks, Ansible) in the same Python process. When the incoming commits change `machine_cli/`, those steps run the old code that was loaded at start against the new checkout. On 2026-10-31 on the Oracle host this happened with the change `ssh-client-config`: the update linked the new `home/core/.ssh/config`, but the new SSH client step (`~/.ssh/cm`, `~/.ssh/config.d/90-legacy`, `known_hosts.d/home`) did not exist in the old code, so the host had no SSH host entries until a second update. A step added or changed by incoming commits should take effect on the update that brings it.

## What Changes

- After the checkout update, `machine update` checks whether `machine_cli/` differs between the revision before and after. If it does, the old code keeps the update lock and starts the checkout's `machine_cli/machine` with a hidden option that runs only the remaining steps, then waits and returns the child's result. If nothing in `machine_cli/` changed, the update runs as before in one process.
- The background job (`machine update --auto`) does the same after its fast-forward. The child runs the dotfile apply, the tool install and the zsh health check and reports the result. The old process keeps the revert: if the child reports a failure, cannot start or crashes, the old code resets to the previous revision and re-applies the dotfile groups with code that matches that revision.
- The hidden option is an internal interface between two versions of `machine`: older code calls newer code with it, so later changes have to keep accepting it. The new checkout lists the protocol versions it accepts in `machine_cli/resume-protocol`; when the running code's version is not listed (for example after a rollback), the update runs the remaining steps itself as before.
- The first update that brings this change still runs the rest with the old code, because the old code does not know about the handoff yet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `update-flow`: added "Update steps run with the new machine code". "Targeted update" stays as it is (`machine_cli/` changes need no extra step; the handoff only changes which code runs the same steps).

Affected profiles: all contexts and devices that run `machine update` or the background job (private and work, desktop, server and container).

## Impact

- Code: `machine_cli/updates.py` (`cmd_update`, `_update_locked` split into the part up to the merge and the remaining steps, handoff), `machine_cli/auto_update.py` (`_apply_auto` split, child result, revert in the parent), `machine_cli/machine` (hidden resume options on `update`).
- Tests: `tests/unit/test_update_and_env.py`, `tests/unit/test_machine_cli.py` (hidden options).
- Docs: Readme update section.
- Where: a git worktree that is not the live main clone, because the change touches `machine_cli/`, which the host runs live from the main clone. This session was already inside the non-live worktree `.claude/worktrees/xenodochial-ellis-c9a21e`, and the repository rules say not to create a worktree from inside one, so the change is made there and not in `.worktrees/update-runs-new-machine-code`.
