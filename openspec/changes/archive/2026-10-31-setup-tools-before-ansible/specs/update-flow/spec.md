# Spec Delta

## ADDED Requirements

### Requirement: Update pulls the env files first
`machine update` SHALL pull the env files before it applies the dotfile groups and the user-space tools, in the same order as `machine setup`, so that questions about local-only keys come before the tool install. The env pull SHALL also run when the host is not set up and the dotfile groups and tools are not applied.

#### Scenario: Order of the update steps
- **WHEN** `machine update` applies the setup and system changes are pending
- **THEN** it pulls the env files, applies the dotfile groups, installs the user-space tools and then runs Ansible, in this order

#### Scenario: Host not set up
- **WHEN** `machine update` runs on a host without `mise` or without the local mise config
- **THEN** the env files are still pulled and the update reports that the host is not set up

### Requirement: Manual update tries every independent step
After the checkout is updated, a manual `machine update` SHALL run each apply step even when an earlier one failed, unless the step needs the failed one, and SHALL report all results at the end. The env pull, the dotfile apply, the tool install and the Ansible apply are steps; the tool install and the zsh health check need the dotfile apply. The background job SHALL keep its revert on the first failure.

#### Scenario: Env pull fails
- **WHEN** the env pull fails during `machine update`, for example because `bw sync` cannot reach the server, and system changes are pending
- **THEN** the dotfile groups and the tools are applied, Ansible runs, and the update ends with an error that names the env pull

#### Scenario: Dotfile apply fails
- **WHEN** the dotfile apply fails during `machine update`
- **THEN** the tool install and the zsh health check are reported as skipped because of it, pending system changes are still applied, and the update ends with an error

#### Scenario: Tool install fails
- **WHEN** the tool install fails during `machine update` and system changes are pending
- **THEN** Ansible runs and the update ends with an error that names the tool install

#### Scenario: Ansible fails after another failure
- **WHEN** the env pull failed and the Ansible apply then fails too
- **THEN** the host config is restored as in "Failed apply restores the host config" and the result names both failed steps

#### Scenario: Background job unchanged
- **WHEN** the dotfile apply or the tool install fails in `machine update --auto`
- **THEN** the job reverts as in "Automatic update safety net" and runs no further step

### Requirement: Update result lists every failed step
When a step of a manual `machine update` failed or was skipped because of a failure, the update SHALL end with one summary that lists each such step with its reason, exit with a non-zero status, set the state to needs-attention naming the failed steps, and keep the details for `machine attention`. A failure in updating the checkout and an interruption by the user SHALL still stop the update at once.

#### Scenario: Summary at the end
- **WHEN** the env pull and the tool install fail during `machine update` and the other steps succeed
- **THEN** the last lines of the output list both steps with their reasons, the exit status is non-zero and the state is needs-attention naming both

#### Scenario: Shell is not replaced
- **WHEN** a manual update ends with a failed step
- **THEN** the shell is not replaced, as for any failed update

#### Scenario: Interrupted
- **WHEN** the user interrupts `machine update` with Ctrl-C during a step
- **THEN** no further step runs
