# Spec Delta

## MODIFIED Requirements

### Requirement: One prompt configuration for both shells
zsh and bash SHALL read the same Starship configuration, which is linked on every host, whatever its context and device. The prompt SHALL show:
- on the first line: the directory, the Git branch and status, the dotfiles update segment, the status of the last command, the Python environment, the command duration and the time
- on the second line: a container marker and the prompt character `❯`

#### Scenario: Same layout in both shells
- **WHEN** the user opens zsh and bash in the same directory
- **THEN** both prompts show the same segments in the same order

#### Scenario: Profile without a full desktop
- **WHEN** the host has the device `server` or `container`
- **THEN** the shared Starship configuration is linked as on desktops
