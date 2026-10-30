# zsh-config-loading Specification

## Purpose
Defines how the zsh configuration is assembled from ordered modules, where host-specific exceptions live, and which tooling is available in zsh and bash.

## Requirements

### Requirement: Ordered module loading
Interactive zsh startup SHALL use an explicit ordered source list in `~/.shell/zsh/init.zsh`, loading the machine profile before the remaining configuration modules. Shared modules SHALL live under `~/.shell/common` and zsh-specific modules under `~/.shell/zsh`. Startup SHALL NOT discover modules by filename prefix or directory glob. Each registered module SHALL execute once per startup in its declared synchronous or deferred stage.

#### Scenario: Normal startup
- **WHEN** an interactive zsh starts
- **THEN** the machine profile is loaded before the modules
- **AND** modules are loaded in the order explicitly declared by the loader, with deferred work retaining its declared dependency order

#### Scenario: Unregistered file
- **WHEN** an additional file exists in a shell module directory but is not registered in the load sequence
- **THEN** startup does not execute that file

#### Scenario: Completion dependency
- **WHEN** startup registers machine completion
- **THEN** it executes once after completion initialization
- **AND** completion initialization and dependent plugins retain their existing deferred ordering during normal interactive startup

#### Scenario: Health-check startup
- **WHEN** the handoff health check starts zsh in its check mode
- **THEN** it runs the same registered deferred work in order before reporting full startup success

### Requirement: Host-local overrides
zsh SHALL load `~/.zshrc-local` when it exists, and it SHALL be used only for genuine single-host exceptions.

#### Scenario: Local file present
- **WHEN** `~/.zshrc-local` exists
- **THEN** it is loaded after the shared configuration

#### Scenario: Local file absent
- **WHEN** `~/.zshrc-local` does not exist
- **THEN** startup continues without error

### Requirement: machine command completion
Tab completion for the `machine` command SHALL be available in both zsh and bash.

#### Scenario: Completion in either shell
- **WHEN** a user types `machine` followed by tab in zsh or in bash
- **THEN** the available subcommands are offered

### Requirement: Externally managed blocks are preserved
Blocks written by external tooling (`ANSIBLE MANAGED BLOCK` in `.profile`, `OSD-PROXY-PACKAGE` in the work module) SHALL be kept unchanged, because the external tool rewrites them otherwise.

#### Scenario: Formatting or editing around a managed block
- **WHEN** the surrounding files are reformatted or edited
- **THEN** the content of each managed block is unchanged
