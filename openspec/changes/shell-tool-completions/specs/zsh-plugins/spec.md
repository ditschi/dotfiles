# Spec Delta

## ADDED Requirements

### Requirement: Available CLI completions load in zsh
Interactive zsh SHALL load completions for installed command-line tools that have a native zsh generator or are supplied by a configured completion provider, after the completion system is initialized and before dependent completion plugins load.

#### Scenario: Tool completion is available
- **WHEN** the deferred completion setup finishes and an installed CLI provides a zsh completion
- **THEN** pressing Tab offers that CLI's supported command or option completions

#### Scenario: Optional CLI is absent
- **WHEN** an installed-tool completion is optional and its CLI is absent
- **THEN** zsh starts without completion-related errors and does not register that CLI's completion
