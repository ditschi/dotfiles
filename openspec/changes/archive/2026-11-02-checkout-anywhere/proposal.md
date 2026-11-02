# Proposal

## Why

The checkout must work at any path, as the repo-layout spec already requires. Today the shell defaults `DOTFILES_REPO` to `~/dotfiles`, which overrides the `machine` symlink; the background update check silently does nothing for a checkout elsewhere; and the agent rule identifies the live checkout by path, so a linked worktree outside `.worktrees/` is mistaken for it. Agents need one reliable way to find the live checkout.

## What Changes

- New command `machine repo`: prints the absolute path of the live checkout (the one `~/.local/bin/machine` links into) on one line and nothing else; exits 1 with a message on stderr when the link is missing or does not point into a checkout. It has no side effects.
- `machine status` shows the live checkout path in its `repo` line.
- The shell derives the default of `DOTFILES_REPO` from the `machine` link instead of `~/dotfiles`; an explicitly set `DOTFILES_REPO` still wins, and `~/dotfiles` stays the fallback when there is no link.
- `dotfiles-update-check-job` finds the checkout the same way, so the background update works for a checkout at any path.
- `machine` finds its repository in the order: explicit `DOTFILES_REPO`, the checkout around its own script, the checkout the link points into, `~/dotfiles`.
- Agent rules (`AGENTS.md`, `openspec/config.yaml`): the live checkout is the output of `machine repo`; the current checkout is live when `git rev-parse --show-toplevel` equals it; new worktrees go to `$(machine repo)/.worktrees/<change-name>` with an absolute path; when `machine repo` fails, no checkout on the host is live.
- Tests: unit tests for `machine repo`, repository detection, the shell default and the update-check job; an integration test that bootstraps from a checkout outside `~/dotfiles` without `DOTFILES_REPO` set and with a stale `~/dotfiles` clone present.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-layout`: "The checkout location is not fixed" gains `machine repo`, the shell default and the background job, and covers a stale `~/dotfiles` next to a checkout elsewhere.
- `update-flow`: the compact `machine status` shows the live checkout path.

## Impact

- Code: `machine_cli/machine` (new `repo` command, excluded from disk-state recording and usage events), `machine_cli/system.py` (`detect_repo`), `machine_cli/commands.py` (`cmd_status`), `home/core/.shell/common/aliases.sh`, `home/core/.local/bin/dotfiles-update-check-job`.
- Agent rules: `AGENTS.md`, `openspec/config.yaml`.
- Tests: `tests/unit/` (new and extended tests), `tests/integration/` (new test, a conftest option to start a container without `DOTFILES_REPO`).
- Profiles: all contexts and devices; containers set `DOTFILES_REPO` explicitly and keep working unchanged.
- Where the change is made: worktree `~/dotfiles/.worktrees/checkout-anywhere` on branch `checkout-anywhere`, because it changes `home/` and `machine_cli/`, which the live checkout serves to the host's shell and tools.
