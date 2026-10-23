# system-provisioning Specification

## Purpose
Defines how Ansible applies packages, tools and system configuration for a host's features.

## Requirements

### Requirement: Ansible applies the feature list
Packages and system configuration SHALL be applied by Ansible through `machine apply`, `machine setup` and `machine update --system`, driven by the host's feature list.

#### Scenario: Host with a feature
- **WHEN** a host has a feature enabled and `machine apply` runs
- **THEN** the packages and configuration of that feature are applied

### Requirement: Package table and local roles
Apt packages per feature SHALL be defined in one table (`packages_by_feature` in `group_vars/all.yml`), so that a new apt-only feature needs a single entry. Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `thinkpad_tuning` and `touch_device`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding an apt-only feature
- **WHEN** a feature needs only apt packages
- **THEN** one entry in `packages_by_feature` is enough

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

### Requirement: LLM CLI features
The features `claude-code` and `copilot-cli` SHALL install those CLIs. Private profiles SHALL default to Claude Code, `work-machine` SHALL default to both, and containers SHALL default to neither, so that container CLIs are opt-in.

#### Scenario: Container profile
- **WHEN** a host has the `container` profile and no LLM feature is selected
- **THEN** no LLM CLI is installed

### Requirement: OpenSpec installed with an LLM CLI
OpenSpec SHALL be installed automatically once an LLM CLI is selected or already installed.

#### Scenario: Work machine
- **WHEN** setup runs on a host with `copilot-cli` selected
- **THEN** OpenSpec is installed

### Requirement: Existing installations are preserved
Provisioning SHALL preserve existing installations where possible: `gh` and `az` with their authentication, an existing Docker provider, an installed `yazi`, and existing LLM CLIs.

#### Scenario: Existing gh login
- **WHEN** `gh` is already installed and authenticated
- **THEN** provisioning does not replace it or remove the login

### Requirement: Root is needed for system roles
The workstation playbook SHALL need root through `become` and SHALL only apply system packages and system configuration. On managed work machines that do not allow root, dotfiles, user-space tools and env management SHALL still be usable without the system roles.

#### Scenario: Host without root
- **WHEN** a work machine cannot become root
- **THEN** the dotfiles, user-space tools and env management still run and the system roles are not applied

### Requirement: Collections and Galaxy roles
`ansible.posix` SHALL be the only required collection, and Galaxy roles SHALL NOT be used; thin local roles are used instead.

#### Scenario: Installing requirements
- **WHEN** the Ansible requirements are installed
- **THEN** only `ansible.posix` is installed

### Requirement: etckeeper on non-container profiles
The feature `etckeeper` SHALL be enabled by default on every profile except `container`.

#### Scenario: Home laptop
- **WHEN** the profile `home-laptop` provides its feature defaults
- **THEN** `etckeeper` is included
