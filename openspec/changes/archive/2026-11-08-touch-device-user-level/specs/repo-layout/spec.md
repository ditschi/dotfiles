# Spec Delta

## MODIFIED Requirements

### Requirement: Layered responsibilities
Desired host state SHALL live in `machine/hosts/<hostname>.yml` (context, device and features), the `machine` CLI SHALL orchestrate setup and handle secrets and Git, `mise` SHALL apply the dotfile groups and install the user-space tools, Ansible SHALL install packages and system configuration that need root, and the Ansible inventory SHALL only describe reachability. Work for the login user that needs no root SHALL be done by `machine` or `mise`, not by Ansible.

#### Scenario: Applying a host
- **WHEN** a host is set up or updated
- **THEN** its context, device and features come from its host config, dotfiles and user-space tools are applied by `mise`, and system packages by Ansible unless the host config switches it off

#### Scenario: User-level desktop setup on a host without Ansible
- **WHEN** a host config sets `ansible: false` and selects a feature whose desktop setup needs no root, such as `touch-device`
- **THEN** `machine` still applies that setup for the login user
