# Spec Delta

## ADDED Requirements

### Requirement: CLI tools include available shell completions
When a selected group adds a command-line tool, its supported Bash and Zsh completions SHALL be enabled when the tool provides them and their required shell support is available. Optional prerequisites SHALL be documented and their absence SHALL NOT break shell startup.

#### Scenario: Tool provides shell completion
- **WHEN** a core or feature group adds a command-line tool with a Bash or Zsh completion
- **THEN** the selected interactive shell loads that completion for the installed tool

#### Scenario: Tool has no supported shell completion
- **WHEN** a core or feature group adds a command-line tool without a Bash or Zsh completion
- **THEN** the tool remains usable and shell startup does not attempt to load a nonexistent completion

#### Scenario: Optional completion prerequisite is absent
- **WHEN** a tool's completion requires an optional shell framework that is not installed
- **THEN** the dependent completion is skipped without a shell startup error and its prerequisite is documented
