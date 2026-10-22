## Purpose

Defines the `sde` and `sdx` launchers for project containers.

## ADDED Requirements

### Requirement: Work-only launchers
The shell wrappers `sde` and `sdx` SHALL exist only on work setups (`01_work.zsh`), and they SHALL call the shared launcher `~/.local/bin/sde`, which uses Docker Compose with the service `dev-env` by default. They SHALL NOT be provided on private machines.

#### Scenario: Private profile
- **WHEN** a shell starts on a private profile
- **THEN** the `sde` and `sdx` wrappers are not defined

### Requirement: Project script takes precedence
`sde` SHALL run the project's `.devcontainer/sde.sh` when it exists, and otherwise run the shared launcher in minimal mode.

#### Scenario: Project with its own script
- **WHEN** `.devcontainer/sde.sh` exists in the current directory and a user runs `sde`
- **THEN** that script runs instead of the shared launcher

#### Scenario: Project without a script
- **WHEN** no `.devcontainer/sde.sh` exists
- **THEN** the shared launcher runs in minimal mode, without the dotfiles

### Requirement: Extended mode
`sdx` SHALL run the shared launcher with `--extended`. In that mode the launcher SHALL mount the host `$HOME`, the dotfiles checkout, the plugin and apt caches and a per-project shell history, and SHALL run the extended setup before the project's post-start step. An interactive session SHALL prefer zsh and fall back to bash when zsh is not available.

#### Scenario: Container with zsh
- **WHEN** a user starts an interactive `sdx` session in a container that has zsh
- **THEN** zsh starts after the setup

#### Scenario: Container without zsh
- **WHEN** the container has no zsh
- **THEN** bash starts

### Requirement: Reuse and one-off runs
The launcher SHALL allow reusing or rebuilding the image (`--rebuild`). An interactive call SHALL attach to an existing project container of the same mode. A one-off command SHALL run in a fresh container without a TTY.

#### Scenario: Second interactive session
- **WHEN** an interactive session starts and a container of the same mode already runs for the project
- **THEN** the session attaches to it

#### Scenario: One-off command
- **WHEN** a user runs `sde -- <command>`
- **THEN** the command runs in a fresh container without a TTY

### Requirement: Container profile inside containers
The dotfiles profile used inside these containers SHALL be `container`, which installs no systemd units and no prompt configs.

#### Scenario: Extended setup in a container
- **WHEN** the extended setup runs inside a project container
- **THEN** the `container` profile is used
