# Spec Delta

## MODIFIED Requirements

### Requirement: Work modules only for work
The work modules (`01_work*.zsh`) SHALL belong to a group that only the profile `work-machine` selects, and they SHALL return early unless `WORK_SETUP=true`.

#### Scenario: Private profile
- **WHEN** the dotfile groups are applied for the profile `home-laptop`
- **THEN** no work module is linked

#### Scenario: Work module without work setup
- **WHEN** a linked work module is sourced and `WORK_SETUP` is not `true`
- **THEN** it returns without effect
