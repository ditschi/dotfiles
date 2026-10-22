## ADDED Requirements

### Requirement: Local bash extension point
`~/.bashrc` SHALL source `~/.bashrc-local` at its end when the file exists, like `~/.zshrc-local` for zsh. Host-specific additions to bash, such as externally managed blocks, live there instead of in the repository file.

#### Scenario: Local file present
- **WHEN** an interactive bash starts and `~/.bashrc-local` exists
- **THEN** it is sourced after the shared configuration

#### Scenario: Local file absent
- **WHEN** `~/.bashrc-local` does not exist
- **THEN** bash starts without error
