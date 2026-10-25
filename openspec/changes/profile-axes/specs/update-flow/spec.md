# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Failed apply restores the host profile`
- TO: `### Requirement: Failed apply restores the host config`

## MODIFIED Requirements

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host config and apply the setup, applying the dotfile groups and the user-space tools before Ansible. System changes and host-config changes SHALL stay explicit.

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

#### Scenario: Home-only change, clean checkout
- **WHEN** the background job finds only home-file changes and the checkout has no local changes
- **THEN** the changes are pulled and applied and the state tells the user to reload the shell

#### Scenario: System change pending
- **WHEN** the incoming changes include a system or host-config change
- **THEN** the background job fast-forwards to the upstream tip, applies the dotfile groups and the user-space tools, does not run Ansible or apply the host config, and the state shows that a system update is available when the changes apply to this host

#### Scenario: Home changes before a system change
- **WHEN** the incoming commits are home-only up to a commit that touches `ansible/**`, packages or the host config
- **THEN** the background job treats all incoming changes together as in "System change pending"; it does not stop before that commit

#### Scenario: Blocked automatic update
- **WHEN** local changes remain that block the fast-forward
- **THEN** nothing is applied and the state is needs-attention with the reason

#### Scenario: System changes are not applied implicitly
- **WHEN** system or host-config changes are pending
- **THEN** they are not applied without the user running the command

#### Scenario: Background job limits
- **WHEN** the background job runs on a clean checkout
- **THEN** it MAY fast-forward to the upstream tip and apply the dotfile groups and user-space tools, and it SHALL only report pending system changes that apply to this host (see "Relevant system changes only")

### Requirement: Failed apply restores the host config
When a local `machine apply` or the apply step of `machine update` fails, including a failing post-apply health check, the previously applied host config SHALL be restored. If the host config had changed, the setup SHALL run once more with the restored one. The post-apply health check SHALL be able to fail and SHALL use only checks that work without root privileges and without cached sudo credentials. Remote applies (`--limit`) SHALL NOT revert.

#### Scenario: Ansible fails after a profile change during update
- **WHEN** `machine update` syncs a changed host config and the Ansible run fails
- **THEN** the previously applied host config is restored and the setup runs again with it

#### Scenario: Health check fails
- **WHEN** the post-apply health check reports a failure
- **THEN** the previously applied host config is restored as for a failed Ansible run

#### Scenario: Unchanged profile
- **WHEN** the apply fails and the host config did not change
- **THEN** the applied host config is kept and the setup is not retried

#### Scenario: Remote apply
- **WHEN** an apply with `--limit` fails
- **THEN** nothing is reverted

### Requirement: Relevant system changes only
The update SHALL report a pending system update only when the files changed since the last successful Ansible run apply to this host, decided without root.

#### Scenario: Always-relevant paths
- **WHEN** playbooks, `ansible/tasks/`, `ansible/group_vars/` or the host config changed
- **THEN** the change applies

#### Scenario: Ignored paths
- **WHEN** only documentation, `dump_*.yml` or the inventory changed
- **THEN** no system update is reported

#### Scenario: Role not enabled on this host
- **WHEN** the incoming change touches only a role that is not enabled for this host
- **THEN** no system update is reported

#### Scenario: Enabled role changed
- **WHEN** the incoming change touches a role that is enabled for this host
- **THEN** the state shows that a system update is available

#### Scenario: Unknown condition
- **WHEN** the enabling condition of a changed role cannot be evaluated
- **THEN** the change counts as applicable

#### Scenario: Host without root
- **WHEN** a host config sets `ansible: false`, or the host has never run Ansible
- **THEN** no system update is reported for it
