## MODIFIED Requirements

### Requirement: One update at a time
Background and manual updates SHALL share a lock so that they cannot run at once, and `machine setup` and `machine update` SHALL ensure that the update-check timer is enabled and, where `loginctl` is available and the host is not a container, that user linger is enabled so the timer also runs without a login session. Enabling linger SHALL be best effort: a failure SHALL be reported with the manual command and SHALL NOT stop setup or update.

#### Scenario: Manual update during a background update
- **WHEN** a manual update starts while a background update runs
- **THEN** it waits or reports that an update is already running

#### Scenario: Linger enabled by setup or update
- **WHEN** `machine setup` or `machine update` runs on a host where linger is off
- **THEN** linger is enabled for the user

#### Scenario: Linger cannot be enabled
- **WHEN** enabling linger fails, for example without admin rights
- **THEN** the command continues and reports how to enable it manually

## ADDED Requirements

### Requirement: Automatic update safety net
After an automatic update the background job SHALL verify that the shell still works. If `chezmoi apply` fails or the zsh health check fails, the job SHALL reset the checkout to the previous revision, re-apply the home files, not retry the failed revision until a manual `machine update` succeeds, and set the state to needs-attention with the reason.

#### Scenario: Zsh breaks after an automatic update
- **WHEN** the zsh health check fails after an automatic update
- **THEN** the checkout is reset to the previous revision, the home files are re-applied and the state is needs-attention with the reason

#### Scenario: Failed revision is not retried
- **WHEN** the background job runs again and the target revision is the one that was reverted
- **THEN** nothing is applied and the state stays needs-attention until a manual `machine update` succeeds

#### Scenario: Manual update clears the failure
- **WHEN** a manual `machine update` succeeds after a reverted automatic update
- **THEN** the failed revision is forgotten and the background job may update again

### Requirement: Failed apply restores the host profile
When a local `machine apply` or the apply step of `machine update` fails, including a failing post-apply health check, the previous host profile SHALL be restored. If the profile had changed, the setup SHALL run once more with the restored profile. The post-apply health check SHALL be able to fail and SHALL use only checks that work without root privileges and without cached sudo credentials. Remote applies (`--limit`) SHALL NOT revert.

#### Scenario: Ansible fails after a profile change during update
- **WHEN** `machine update` syncs a changed host profile and the Ansible run fails
- **THEN** the previous host profile is restored and the setup runs again with it

#### Scenario: Health check fails
- **WHEN** the post-apply health check reports a failure
- **THEN** the previous host profile is restored as for a failed Ansible run

#### Scenario: Unchanged profile
- **WHEN** the apply fails and the host profile did not change
- **THEN** the profile is kept and the setup is not retried

#### Scenario: Remote apply
- **WHEN** an apply with `--limit` fails
- **THEN** nothing is reverted
