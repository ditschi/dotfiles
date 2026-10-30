# Spec Delta

## ADDED Requirements

### Requirement: Available CLI completions load in bash
Interactive bash SHALL load completions for installed command-line tools that have a native bash generator or are supplied by a configured completion provider, including when bash remains the active fallback shell.

#### Scenario: Tool completion is available
- **WHEN** an installed CLI provides a bash completion and interactive bash starts
- **THEN** pressing Tab offers that CLI's supported command or option completions

#### Scenario: Optional CLI is absent
- **WHEN** an installed-tool completion is optional and its CLI is absent
- **THEN** bash starts without completion-related errors and does not register that CLI's completion

#### Scenario: Optional completion framework is absent
- **WHEN** a CLI's Bash completion requires the optional `bash-completion` framework and that framework is unavailable
- **THEN** Bash starts without completion-related errors and skips only that CLI's completion
