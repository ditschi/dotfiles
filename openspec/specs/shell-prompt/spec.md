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

### Requirement: Container marker
The prompt SHALL show 🐳 in front of the prompt character when the shell runs inside a container, and nothing on a host.

#### Scenario: Inside Docker
- **WHEN** a shell runs in a Docker container
- **THEN** the prompt shows 🐳

#### Scenario: On a host
- **WHEN** a shell runs directly on a host
- **THEN** no container marker is shown

### Requirement: Remote context
The Starship prompt SHALL show `user@hostname` in front of the time when the shell runs over SSH, in zsh and in bash. In a root shell it SHALL show the user name also without SSH. Otherwise it SHALL show neither.

#### Scenario: SSH session
- **WHEN** an interactive zsh or bash runs over SSH
- **THEN** the first prompt line shows `user@hostname` in front of the time

#### Scenario: Local session
- **WHEN** a non-root shell runs locally
- **THEN** neither user name nor hostname is shown

#### Scenario: Local root shell
- **WHEN** a root shell runs locally
- **THEN** the user name is shown, without the hostname

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
