# terminal-multiplexer Specification

## Purpose
Defines which terminal multiplexers every host gets and how shells relate to them, so that zellij is available everywhere without changing how a shell starts.

## Requirements

### Requirement: zellij on every host without root
Every host, whatever its profile, SHALL have zellij installed as a user-space tool from mise, with its version pinned in the repository lockfile for linux-x64 and linux-arm64. No root and no Ansible run SHALL be needed.

#### Scenario: Host without root
- **WHEN** `machine setup` runs on a host that cannot become root
- **THEN** `zellij` is found by name in a new interactive zsh and bash

#### Scenario: arm64 host
- **WHEN** a Raspberry Pi with an arm64 CPU installs the tools
- **THEN** the pinned arm64 build of zellij is installed

#### Scenario: Container profile
- **WHEN** a host with the device `container` is set up
- **THEN** zellij is installed like the other core shell tools

### Requirement: zellij uses its default key bindings
zellij SHALL run with its built-in default key bindings, with no key remapped by the dotfiles. Ctrl+G SHALL lock and unlock zellij, so that while it is locked all keys reach the program in the pane.

#### Scenario: fzf file search inside zellij
- **WHEN** the user presses Ctrl+G, then Ctrl+T in a zsh pane
- **THEN** the fzf file search opens in the shell

#### Scenario: fzf outside zellij
- **WHEN** the user presses Ctrl+T in a shell that does not run inside zellij
- **THEN** the fzf file search opens, as before

### Requirement: Mouse selection in zellij goes to the primary selection
In a graphical session (Wayland or X11), text selected with the mouse inside zellij without a modifier key SHALL be copied to the primary selection when the mouse is released, so that a middle click pastes it. Without a graphical session the selection SHALL be discarded without an error.

#### Scenario: Copy a command from output
- **WHEN** the user selects a command in earlier output inside zellij on a Wayland desktop and middle-clicks at the prompt
- **THEN** the selected command is pasted

#### Scenario: Session over SSH
- **WHEN** the user selects text inside zellij on a host without a graphical session
- **THEN** zellij shows no error and the selection is not copied

### Requirement: Shells do not start a multiplexer automatically
Interactive zsh and bash SHALL start as plain shells and SHALL NOT launch zellij or tmux on their own; the user starts a multiplexer by hand.

#### Scenario: New terminal window
- **WHEN** the user opens a new terminal window or logs in over SSH
- **THEN** a plain zsh (or bash) starts, not a zellij session

#### Scenario: Manual start
- **WHEN** the user runs `zellij` in a shell
- **THEN** a zellij session starts with zsh in its first pane

### Requirement: tmux stays available
Adding zellij SHALL NOT remove tmux or change its configuration.

#### Scenario: Existing tmux user
- **WHEN** zellij has been added and the user runs `tmux`
- **THEN** tmux starts with the existing `~/.tmux.conf`
