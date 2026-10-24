# Spec Delta

## ADDED Requirements

### Requirement: opencode comes from mise
opencode SHALL be installed by mise from the LLM fragment and pinned in the lockfile. The dotfiles SHALL NOT add `~/.opencode/bin` to `PATH`.

#### Scenario: New interactive shell
- **WHEN** an interactive bash or zsh starts after `machine setup`
- **THEN** `opencode` is found through mise activation

#### Scenario: Leftover installer line
- **WHEN** an installer appended a PATH export to a shared shell file
- **THEN** the tool is added to a mise fragment instead and the line is not kept in the repository

### Requirement: PATH for manual npm global installs
Interactive zsh and bash SHALL have `~/.npm-global/bin` on `PATH`, set in the shared environment module that both shells load, whether or not the directory exists. `machine` SHALL NOT set an npm prefix.

#### Scenario: Tool installed with npm install -g
- **WHEN** a user set `prefix` to `~/.npm-global` in `~/.npmrc` and installed a tool with `npm install -g`
- **THEN** the tool is found in zsh and bash
