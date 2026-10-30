# Spec Delta

## MODIFIED Requirements

### Requirement: Shared module subset in bash

An interactive Bash session that stays in Bash SHALL load aliases, environment and machine-profile modules from `~/.shell/common`, with Bash-specific history and integration from `~/.shell/bash`, through an explicit ordered source list in `~/.shell/bash/init.bash`. Startup SHALL NOT automatically execute unregistered files. Non-interactive Bash SHALL return before loading the interactive configuration.

#### Scenario: Interactive bash

- **WHEN** an interactive bash session stays in bash
- **THEN** the shared alias, environment and machine-profile modules and the Bash-specific history module are loaded in the declared order
- **AND** registered modules execute once per startup without loading zsh-only code

#### Scenario: Unregistered file

- **WHEN** an additional file exists in a shell module directory but is not registered in the load sequence
- **THEN** Bash startup does not execute that file

#### Scenario: Non-interactive bash

- **WHEN** a non-interactive Bash process sources `~/.bashrc`
- **THEN** it returns before loading the interactive modules or running the shell handoff

### Requirement: Work modules only on work hosts

Bash SHALL load shared work modules from `~/.shell/work/common` only when `WORK_SETUP` is `true` and the work module files exist on the host. Work tools SHALL load before the work environment that depends on them. Bash SHALL NOT load zsh-only work helpers.

#### Scenario: Work machine

- **WHEN** `WORK_SETUP` is `true` and the work module files exist
- **THEN** the work tools and work environment modules are loaded in bash, in that order

#### Scenario: Dev container or private host

- **WHEN** `WORK_SETUP` is not `true` or the work module files do not exist
- **THEN** no work module is loaded in bash

#### Scenario: Zsh-only work helper

- **WHEN** shared work modules are loaded in Bash
- **THEN** the LDAP helpers under `~/.shell/work/zsh` are not loaded
