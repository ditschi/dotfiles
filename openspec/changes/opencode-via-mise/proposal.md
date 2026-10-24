# Proposal

## Why

On the current host, opencode was installed with its own installer, which appended `export PATH=$HOME/.opencode/bin:$PATH` to `.zshrc` only. That line is a local change in the checkout that blocks `machine update`, and bash does not get it. opencode should come from mise like the other LLM CLIs. Then it is on `PATH` in both shells through mise activation, pinned in the lockfile and installed on every host without manual steps. npm CLIs such as `thunderbird-cli` are installed by mise too, so `machine` does not set an npm user prefix. For tools installed by hand with `npm install -g` into `~/.npm-global` (a prefix the user sets in `~/.npmrc`), both shells get `~/.npm-global/bin` on `PATH`.

## What Changes

- `opencode` (mise registry, backend `npm:@opencode/cli`) is added to the LLM fragment `home/core/.config/mise/conf.d/30-llm.toml` and pinned in `mise.lock`.
- The shared environment module `~/.zsh/config/01_env.zsh`, which zsh and bash both load, prepends `~/.npm-global/bin` to `PATH`, also when the directory does not exist.
- No PATH export for `~/.opencode/bin`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-tools`: opencode is a mise tool.

Affected profiles: the same hosts that get the LLM fragment today (all groups that include `core`).

## Impact

- `home/core/.config/mise/conf.d/30-llm.toml`, `home/core/.zsh/config/01_env.zsh`, `home/core/.config/mise/mise.lock` and `.mise/locks/`, Readme.
- Hosts with a manual opencode install (`~/.opencode`) can remove it after the update; mise's binary takes over through `PATH`.
