## Why

`machine update` is slower and less precise than it needs to be: it applies everything even when only a few files changed, and any local change in a symlinked file blocks the update, although some of these changes (for example host-only Git settings) are expected and already have logic that moves them into local config. Resolving expected local changes first lets the update tell real changes that need manual checking from changes it can simply apply over. This is the foundation for automatic updates (`update-state-and-hint`, `auto-update`).

## What Changes

- Before an update, the known local-change resolvers run. The existing Git config relocation becomes the first entry of a reusable resolver mechanism; the second moves externally managed blocks from `~/.bashrc` into a new `~/.bashrc-local`.
- The update fast-forwards with `git fetch` and `git merge --ff-only` and stops only when a locally changed file is also changed upstream or the history diverged. Other local changes are reported as a notice.
- `machine update` runs only the steps the incoming changes need.
- `machine update --check` (with `--json`) shows the result read-only; `machine status` uses it.
- A lock shared by background and manual updates; `machine update` ensures the update-check timer is enabled.

## Capabilities

### Modified Capabilities
- `update-flow`: "Update never discards local work" changes its blocking rule; new requirements "Targeted update", "Read-only update check" and "One update at a time".
- `bash-shared-config`: new "Local bash extension point".

Profiles: all.

## Impact

`home/dot_local/lib/machine_cli/commands.py` (`cmd_update`, `cmd_status`), `tools.py` (`sanitize_git_config`, `git_dirty`), `machine/gitconfig.py`, `home/dot_bashrc`, `tests/unit`, Readme "Updates".

Depends on nothing. `update-state-and-hint` and `auto-update` build on it.
