# Spec Delta

## MODIFIED Requirements

### Requirement: Package table and local roles
Apt packages per feature SHALL be defined in one table (`packages_by_feature` in `group_vars/all.yml`), so that a new apt-only feature needs a single entry. Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `thinkpad_tuning`, `thunderbird` and `touch_device`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding an apt-only feature
- **WHEN** a feature needs only apt packages
- **THEN** one entry in `packages_by_feature` is enough

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible
