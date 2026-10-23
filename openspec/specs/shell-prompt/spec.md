# shell-prompt Specification

## Purpose
Defines the prompt of the interactive shells: Starship with one shared configuration in zsh and bash, which differ only in the colour of the prompt character, and a plain built-in prompt when Starship is missing.

## Requirements

### Requirement: Starship prompt in bash
Interactive bash SHALL use the Starship prompt with the shared configuration when Starship is installed.

#### Scenario: Starship installed
- **WHEN** an interactive bash starts and Starship is installed
- **THEN** the Starship prompt is shown

#### Scenario: Starship not installed
- **WHEN** an interactive bash starts and Starship is not installed
- **THEN** bash shows a simple prompt that includes the update segment, without error output

### Requirement: Starship prompt in zsh
Interactive zsh SHALL use the Starship prompt when Starship is installed. The prompt SHALL appear without waiting for the deferred plugins.

#### Scenario: Starship installed
- **WHEN** an interactive zsh starts and Starship is installed
- **THEN** the Starship prompt is shown with the shared configuration

#### Scenario: Starship not installed
- **WHEN** an interactive zsh starts and Starship is not installed
- **THEN** zsh shows a simple built-in prompt that includes the update segment, without error output

### Requirement: One prompt configuration for both shells
zsh and bash SHALL read the same Starship configuration, which is linked on every profile. The prompt SHALL show:
- on the first line: the directory, the Git branch and status, the dotfiles update segment, the status of the last command, the Python environment, the command duration and the time
- on the second line: a container marker and the prompt character `❯`

#### Scenario: Same layout in both shells
- **WHEN** the user opens zsh and bash in the same directory
- **THEN** both prompts show the same segments in the same order

#### Scenario: Profile without a full desktop
- **WHEN** the host profile is `rpi-zero` or `container`
- **THEN** the shared Starship configuration is linked as on the other profiles

### Requirement: Shell indicator
The prompt character `❯` SHALL be bold green in zsh and bold purple in bash. A failed command SHALL be shown by the status segment, not by the colour of the prompt character.

#### Scenario: zsh prompt
- **WHEN** an interactive zsh shows its prompt
- **THEN** the prompt character is green

#### Scenario: bash prompt
- **WHEN** an interactive bash shows its prompt
- **THEN** the prompt character is purple

#### Scenario: Failed command
- **WHEN** the previous command exited non-zero
- **THEN** the status segment shows the error, and the prompt character keeps its shell colour

### Requirement: Container marker
The prompt SHALL show 🐳 in front of the prompt character when the shell runs inside a container, and nothing on a host.

#### Scenario: Inside Docker
- **WHEN** a shell runs in a Docker container
- **THEN** the prompt shows 🐳

#### Scenario: On a host
- **WHEN** a shell runs directly on a host
- **THEN** no container marker is shown
