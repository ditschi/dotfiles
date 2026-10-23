# Spec Delta

## MODIFIED Requirements

### Requirement: Package table and local roles
Apt packages per feature SHALL be defined in one table (`packages_by_feature` in `group_vars/all.yml`), so that a new apt-only feature needs a single entry. Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `thinkpad_tuning` and `touch_device`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding an apt-only feature
- **WHEN** a feature needs only apt packages
- **THEN** one entry in `packages_by_feature` is enough

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

### Requirement: Root is needed for system roles
The workstation playbook SHALL need root through `become` and SHALL only apply system packages and system configuration. On managed work machines that do not allow root, dotfiles, user-space tools and env management SHALL still be usable without the system roles.

#### Scenario: Host without root
- **WHEN** a work machine cannot become root
- **THEN** the dotfiles, user-space tools and env management still run and the system roles are not applied

### Requirement: OpenSpec installed with an LLM CLI
OpenSpec SHALL be installed automatically once an LLM CLI is selected or already installed.

#### Scenario: Work machine
- **WHEN** setup runs on a host with `copilot-cli` selected
- **THEN** OpenSpec is installed

## REMOVED Requirements

### Requirement: Node tools on every profile
**Reason**: Node is installed by `mise` as a user-space tool and no longer by an Ansible role.
**Migration**: See `user-tools`. Bash and zsh load Node through `mise` activation; an existing NVM default of Node 22 or newer is not removed by the update.
