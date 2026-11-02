# Spec Delta

## MODIFIED Requirements

### Requirement: One prompt configuration for both shells
zsh and bash SHALL read the same Starship configuration, which is linked on every host, whatever its context and device. The prompt SHALL show:
- on the first line: the directory, the Git branch and status, the dotfiles update segment, the status of the last command, the active Python virtualenv, the command duration, the remote context (`user@hostname`) and the time
- on the second line: an SSH marker, a container marker and the prompt character `❯`

#### Scenario: Same layout in both shells
- **WHEN** the user opens zsh and bash in the same directory
- **THEN** both prompts show the same segments in the same order

#### Scenario: Profile without a full desktop
- **WHEN** the host has the device `server` or `container`
- **THEN** the shared Starship configuration is linked as on desktops

### Requirement: Shell indicator
The prompt character `❯` SHALL be bold green in zsh and bold blue in bash. After a failed command it SHALL be red in zsh and orange in bash, and the status segment SHALL show the error.

#### Scenario: zsh prompt
- **WHEN** an interactive zsh shows its prompt
- **THEN** the prompt character is green

#### Scenario: bash prompt
- **WHEN** an interactive bash shows its prompt
- **THEN** the prompt character is blue

#### Scenario: Failed command
- **WHEN** the previous command exited non-zero
- **THEN** the status segment shows the error, and the prompt character is red in zsh and orange in bash

## ADDED Requirements

### Requirement: SSH marker
The prompt SHALL show `💻 ssh` on the second line, in front of the container marker and the prompt character, when the shell runs over SSH, and nothing otherwise.

#### Scenario: SSH session
- **WHEN** an interactive zsh or bash runs over SSH
- **THEN** the second prompt line starts with `💻 ssh`

#### Scenario: Local session
- **WHEN** a shell runs locally
- **THEN** no SSH marker is shown

### Requirement: Git status counts
In a Git repository the prompt SHALL show a git icon and the branch name, followed by the number of changed, new, staged, conflicting and deleted files, the commits ahead of and behind the upstream, and ✓ when the branch is in sync with its upstream.

#### Scenario: Local changes
- **WHEN** a repository has one changed and one new file
- **THEN** the Git status shows `!1` and `?1` after the branch name

#### Scenario: In sync with the upstream
- **WHEN** the branch has an upstream and is neither ahead nor behind
- **THEN** the Git status shows ✓

### Requirement: Python virtualenv segment
The prompt SHALL show 🐍 with the name of the active Python virtualenv only while a virtualenv is active, without the Python version.

#### Scenario: Virtualenv active
- **WHEN** a virtualenv named `myenv` is active
- **THEN** the prompt shows `🐍 (myenv)`

#### Scenario: Python project without a virtualenv
- **WHEN** the directory contains Python files and no virtualenv is active
- **THEN** no Python segment is shown
