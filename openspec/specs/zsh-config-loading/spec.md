# zsh-config-loading Specification

## Purpose
Defines how the zsh configuration is assembled from ordered modules, where host-specific exceptions live, and which tooling is available in zsh and bash.

## Requirements

### Requirement: Ordered module loading
The zsh startup SHALL load the machine profile first and then every module in the config directory in lexical order of its numeric file prefix, so that modules that must come first are loaded first.

#### Scenario: Normal startup
- **WHEN** an interactive zsh starts
- **THEN** the machine profile is loaded before the modules
- **AND** modules are loaded in lexical order of their `NN_topic` names

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
