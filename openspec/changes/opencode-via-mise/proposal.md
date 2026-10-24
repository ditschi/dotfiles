# Proposal

## Why

On the current host, opencode was installed with its own installer, which appended `export PATH=$HOME/.opencode/bin:$PATH` to `.zshrc` only. That line is a local change in the checkout that blocks `machine update`, and bash does not get it. opencode should come from mise like the other LLM CLIs. Then it is on `PATH` in both shells through mise activation, pinned in the lockfile and installed on every host without manual steps. npm CLIs such as `thunderbird-cli` are installed by mise too, so `machine` does not set an npm user prefix.

## What Changes

- `opencode` (mise registry, backend `npm:@opencode/cli`) is added to the LLM fragment `home/core/.config/mise/conf.d/30-llm.toml` and pinned in `mise.lock`.
- No PATH exports for `~/.opencode/bin` or `~/.npm-global/bin`: tools come from mise, nothing is installed with `npm install -g`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-tools`: opencode is a mise tool.

Affected profiles: the same hosts that get the LLM fragment today (all groups that include `core`).

## Impact

- `home/core/.config/mise/conf.d/30-llm.toml`, `home/core/.config/mise/mise.lock` and `.mise/locks/`, Readme.
- Hosts with a manual opencode install (`~/.opencode`) or manual `npm install -g` tools (`~/.npm-global`) can remove them after the update; mise's binaries take over through `PATH`.
