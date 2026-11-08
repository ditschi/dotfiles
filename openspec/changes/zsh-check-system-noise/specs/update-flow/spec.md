# Spec Delta

## ADDED Requirements

### Requirement: Zsh warnings do not fail updates
A zsh health check that passes with a warning (error output only from the full trial start) SHALL count as passed in the automatic update, the manual `machine update` and the post-apply health check. `machine` SHALL show or log the warning, and SHALL NOT revert, restore or set needs-attention because of it.

#### Scenario: Automatic update with a zsh warning
- **WHEN** the zsh health check passes with a warning after an automatic update
- **THEN** the update is kept, the warning is logged and the checkout is not reset

#### Scenario: Manual update with a zsh warning
- **WHEN** the zsh health check passes with a warning at the end of a manual update
- **THEN** the warning is shown, the step counts as passed and the state is not set to needs-attention because of it

#### Scenario: Apply with a zsh warning
- **WHEN** Ansible succeeds and the post-apply health check passes with a zsh warning
- **THEN** the apply succeeds, the warning is logged and nothing is restored
