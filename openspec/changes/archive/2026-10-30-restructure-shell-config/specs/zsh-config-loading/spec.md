# Spec Delta

## MODIFIED Requirements

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
