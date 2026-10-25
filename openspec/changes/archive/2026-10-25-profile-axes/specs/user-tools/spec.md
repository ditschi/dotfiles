# Spec Delta

## MODIFIED Requirements

### Requirement: opencode comes from mise
opencode SHALL be installed by mise from the `opencode` group, which the feature `opencode` selects, and pinned in the lockfile. The dotfiles SHALL NOT add `~/.opencode/bin` or `~/.npm-global/bin` to `PATH`.

#### Scenario: New interactive shell
- **WHEN** an interactive bash or zsh starts after `machine setup` on a host with the feature `opencode`
- **THEN** `opencode` is found through mise activation

#### Scenario: Leftover installer line
- **WHEN** an installer appended a PATH export to a shared shell file
- **THEN** the tool is added to a mise fragment instead and the line is not kept in the repository

## ADDED Requirements

### Requirement: Core tools on every host
The `core` group SHALL install on every host, containers included: Git and Git LFS, the shell tools (fzf, zoxide, eza, fd, Starship, jq, delta, tealdeer, tmux, zellij), gh, yazi, Node.js and uv. LLM command line tools and OpenSpec SHALL NOT be in `core`.

#### Scenario: Container
- **WHEN** a container is set up without any LLM feature
- **THEN** Starship, yazi and gh are installed and no LLM CLI or OpenSpec is installed

### Requirement: LLM tools per feature
Claude Code, Copilot CLI and opencode SHALL each be in their own group (`claude`, `copilot`, `opencode`), selected by the features `claude-code`, `copilot-cli` and `opencode`. OpenSpec SHALL be in its own group `openspec`, selected by each of these three features, so that it is declared once and installed whenever any LLM CLI is selected.

#### Scenario: Only Copilot
- **WHEN** a host has `copilot-cli` and neither `claude-code` nor `opencode`
- **THEN** Copilot CLI and OpenSpec are installed, Claude Code and opencode are not

#### Scenario: Feature removed
- **WHEN** the last LLM feature is removed from a host config and the setup runs
- **THEN** the `openspec` group is no longer selected and its tools are no longer on the `PATH`
