# Spec Delta

## ADDED Requirements

### Requirement: Bootstrap installs mise
The bootstrap script SHALL install `mise` for the user when it is missing, without root, before `machine setup` applies the dotfile groups and the user-space tools, and SHALL leave an installed `mise` as it is.

#### Scenario: mise missing
- **WHEN** bootstrap runs and `mise` is not installed
- **THEN** `mise` is installed to the user's home and `machine setup` runs

#### Scenario: mise present
- **WHEN** bootstrap runs and `mise` is installed
- **THEN** it is not reinstalled
