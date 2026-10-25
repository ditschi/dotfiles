# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: etckeeper on non-container profiles`
- TO: `### Requirement: etckeeper outside containers
The feature `etckeeper` SHALL be preselected on every host except those with the device `container`.

#### Scenario: Home laptop
- **WHEN** a private desktop takes its feature defaults
- **THEN** `etckeeper` is included

### Requirement: System roles run with root unless switched off
The workstation playbook SHALL need root through `become` and SHALL only apply system packages and system configuration. Root SHALL be assumed on every host; a host whose host config sets `ansible: false` SHALL skip the playbook, while dotfiles, user-space tools and env management still run.

#### Scenario: Host without root
- **WHEN** a host config sets `ansible: false`
- **THEN** the dotfiles, user-space tools and env management still run and the system roles are not applied

#### Scenario: Root not available without the setting
- **WHEN** a host without `ansible: false` cannot become root
- **THEN** the Ansible run fails with a message that names the setting
