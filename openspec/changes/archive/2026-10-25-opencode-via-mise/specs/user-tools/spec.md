# Spec Delta

## ADDED Requirements

### Requirement: opencode comes from mise
opencode SHALL be installed by mise from the LLM fragment and pinned in the lockfile. The dotfiles SHALL NOT add `~/.opencode/bin` or `~/.npm-global/bin` to `PATH`.

#### Scenario: New interactive shell
- **WHEN** an interactive bash or zsh starts after `machine setup`
- **THEN** `opencode` is found through mise activation

#### Scenario: Leftover installer line
- **WHEN** an installer appended a PATH export to a shared shell file
- **THEN** the tool is added to a mise fragment instead and the line is not kept in the repository
