## ADDED Requirements

### Requirement: Bash prompt survives host-local overrides
Interactive bash SHALL keep the Starship prompt when `~/.bashrc-local` replaces `PROMPT_COMMAND` or `PS1`, and commands the local file adds to `PROMPT_COMMAND` SHALL still run before each prompt.

#### Scenario: Local file replaces PROMPT_COMMAND
- **WHEN** Starship is installed and `~/.bashrc-local` assigns a new value to `PROMPT_COMMAND`
- **THEN** the Starship prompt is rendered at the next prompt
- **AND** the commands of the assigned value run before it

#### Scenario: Local file replaces PS1
- **WHEN** Starship is installed and `~/.bashrc-local` assigns a new value to `PS1`
- **THEN** the Starship prompt replaces it at the next prompt

#### Scenario: Local file leaves the prompt alone
- **WHEN** `~/.bashrc-local` does not touch `PROMPT_COMMAND`
- **THEN** the prompt hook is not wrapped a second time

#### Scenario: Starship not installed
- **WHEN** Starship is not installed and `~/.bashrc-local` replaces `PROMPT_COMMAND`
- **THEN** the replacement stays in effect and bash starts without error output
