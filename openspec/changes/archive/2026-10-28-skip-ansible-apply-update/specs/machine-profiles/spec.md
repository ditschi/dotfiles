## ADDED Requirements

### Requirement: Ansible can be skipped for one invocation
Users SHALL be able to skip Ansible and system provisioning for one apply or update invocation without changing persistent host policy. Update SHALL still merge repository changes and apply dotfiles and user-space tools; skipped system changes SHALL remain detectable as pending.

#### Scenario: Apply explicitly skips Ansible
- **WHEN** a user runs `machine apply --skip-ansible` for a host whose config allows Ansible
- **THEN** host config synchronization completes, Ansible and bootstrap system provisioning do not run, and the saved `ansible` setting remains true

#### Scenario: Update explicitly skips Ansible
- **WHEN** a user runs `machine update --skip-ansible` while repository changes include dotfiles, user-space tools, and system files
- **THEN** repository changes, dotfiles, and user-space tools are applied, Ansible does not run, and system changes remain detectable as pending

#### Scenario: Skip is per invocation
- **WHEN** the next `machine apply` or `machine update` runs without `--skip-ansible` and the host config allows Ansible
- **THEN** normal Ansible behavior runs for applicable system changes
