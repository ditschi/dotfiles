# bash-shared-config Specification

## Purpose
Defines which part of the zsh configuration bash shares, so that bash sessions (containers, hosts without zsh, manually started bash) get the same basic environment as zsh.

## Requirements

### Requirement: Shared module subset in bash
An interactive bash session SHALL load the shared modules for aliases, environment, pyenv and history, plus the shared machine profile.

#### Scenario: Interactive bash
- **WHEN** an interactive bash session stays in bash
- **THEN** the alias, environment, pyenv and history modules and the machine profile are loaded

### Requirement: Work modules only on work hosts
bash SHALL load the work modules only when `WORK_SETUP` is `true` and the work module file exists on the host.

#### Scenario: Work machine
- **WHEN** `WORK_SETUP` is `true` and the work module file exists
- **THEN** the work modules are loaded in bash

#### Scenario: Dev container or private host
- **WHEN** `WORK_SETUP` is not `true` or the work module file does not exist
- **THEN** no work module is loaded in bash

### Requirement: Shared modules stay bash-compatible
Every module that bash loads MUST remain valid bash.

#### Scenario: Module loaded by both shells
- **WHEN** a shared module is sourced by bash
- **THEN** it completes without syntax errors

### Requirement: Local bash extension point
`~/.bashrc` SHALL source `~/.bashrc-local` at its end when the file exists, like `~/.zshrc-local` for zsh. Host-specific additions to bash, such as externally managed blocks, live there instead of in the repository file.

#### Scenario: Local file present
- **WHEN** an interactive bash starts and `~/.bashrc-local` exists
- **THEN** it is sourced after the shared configuration

#### Scenario: Local file absent
- **WHEN** `~/.bashrc-local` does not exist
- **THEN** bash starts without error
