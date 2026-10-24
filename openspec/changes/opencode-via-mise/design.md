# Design

## Context

Node and npm come from mise (`node = "lts"` in `20-tools.toml`). mise's `npm:` backend installs each npm CLI into its own directory and puts it on `PATH` through activation. zsh loads `~/.zsh/config/01_env.zsh`, and `~/.bashrc` sources it too. See proposal.md for the motivation.

## Decisions

- **opencode from mise (owner decision).** Registry name `opencode`, which resolves to `npm:@opencode/cli`. The `aqua:anomalyco/opencode` backend was not used because it lags behind (1.19.4 against 2.1.4 on 2026-10-24).
- **No npm prefix from `machine` (owner decision).** npm CLIs of the dotfiles come from mise.
- **No `~/.npm-global/bin` on PATH (owner decision).** All npm CLIs come from mise; nothing is installed globally with npm, so the dotfiles carry no PATH entry for it.
