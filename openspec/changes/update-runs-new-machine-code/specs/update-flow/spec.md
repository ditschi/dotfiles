# Spec Delta

## ADDED Requirements

### Requirement: Update steps run with the new machine code
When `machine_cli/` differs between the revision before and after the checkout update and the new code accepts the handoff, `machine update` and the background job SHALL run the remaining steps with the `machine` code of the new revision, while the process that started the update keeps the update lock. The background job SHALL keep its revert on the first failure, also when the new code does not start or stops without a result.

#### Scenario: Incoming commits add an apply step
- **WHEN** a user runs `machine update` and the incoming commits change `machine_cli/` so that the dotfile apply does one more thing
- **THEN** that new part of the dotfile apply runs in this update, not only in the next one

#### Scenario: Automatic update with changed machine code
- **WHEN** the background job fast-forwards over commits that change `machine_cli/` and home files
- **THEN** the dotfile apply, the tool install and the zsh health check run with the new code, and the state is "updated" when they succeed

#### Scenario: New code fails in the automatic update
- **WHEN** the background job hands over to the new code and a step fails, or the new code stops without a result
- **THEN** the checkout is reset to the previous revision, the dotfile groups are re-applied with the code of that revision and the state is needs-attention with the reason, as in "Automatic update safety net"

#### Scenario: New code stops in a manual update
- **WHEN** a manual `machine update` hands over to the new code and it stops with an error before it records a result
- **THEN** the update exits with a non-zero status and the state is needs-attention

#### Scenario: Machine code unchanged
- **WHEN** the incoming commits do not change `machine_cli/`
- **THEN** the update runs all steps in the process that started it

#### Scenario: New code without the handoff
- **WHEN** the incoming commits change `machine_cli/` to a revision that does not accept the handoff, for example a rollback
- **THEN** the update runs all steps in the process that started it and succeeds as before

#### Scenario: Lock held during the handoff
- **WHEN** the background timer fires while a manual update runs the remaining steps with the new code
- **THEN** the background job finds the update lock taken and skips
