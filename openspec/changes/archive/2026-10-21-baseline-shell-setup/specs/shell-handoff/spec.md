# Spec Delta

## Purpose

Defines how an interactive bash session hands over to the preferred shell on hosts where the account's login shell cannot be changed, so that the customised zsh is used where it is available.

## ADDED Requirements

### Requirement: Customised zsh is preferred when installed
An interactive top-level bash session SHALL hand over to zsh with the dotfiles customisation when zsh is installed, unless the user has explicitly configured another shell.

#### Scenario: zsh installed, no override
- **WHEN** a user opens an interactive top-level bash session and zsh is installed
- **THEN** the session is replaced by a zsh login shell

#### Scenario: zsh not installed
- **WHEN** a user opens an interactive top-level bash session and zsh is not installed
- **THEN** the session stays in bash

### Requirement: Manually started bash is respected
The handoff SHALL NOT replace a bash session that the user started manually, from another shell or inside another bash, so that the user ends up in bash as asked.

#### Scenario: bash started from another shell
- **WHEN** the user starts bash from another interactive shell (for example zsh)
- **THEN** the session stays in bash

#### Scenario: nested bash
- **WHEN** the user starts bash inside an existing shell level
- **THEN** the session stays in bash

### Requirement: Explicit preferred shell
A valid `~/.preferred-shell` SHALL take precedence over the default handoff: the named shell is used if it is installed, and a value of bash keeps the session in bash.

#### Scenario: preferred shell set and installed
- **WHEN** `~/.preferred-shell` names an installed shell other than bash
- **THEN** the session is replaced by that shell as a login shell, also inside Docker

#### Scenario: preferred shell set to bash
- **WHEN** `~/.preferred-shell` names bash
- **THEN** the session stays in bash

### Requirement: Handoff works without changing the login shell
The handoff SHALL NOT depend on changing the account's login shell. Changing it is possible on private hosts but not on work hosts, where the account is centrally managed.

#### Scenario: Work host without chsh
- **WHEN** the setup is used on a work host whose account is not in the local password database
- **THEN** zsh is reached through the bash handoff
