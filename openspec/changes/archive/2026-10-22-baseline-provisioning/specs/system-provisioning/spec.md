## Purpose

Defines how Ansible applies packages, tools and system configuration for a host's features.

## ADDED Requirements

### Requirement: Ansible applies the feature list
Packages and system configuration SHALL be applied by Ansible through `machine apply`, `machine setup` and `machine update --system`, driven by the host's feature list.

#### Scenario: Host with a feature
- **WHEN** a host has a feature enabled and `machine apply` runs
- **THEN** the packages and configuration of that feature are applied

### Requirement: Package table and local roles
Apt packages per feature SHALL be defined in one table (`packages_by_feature` in `group_vars/all.yml`), so that a new apt-only feature needs a single entry. Larger features SHALL be local roles: `az_cli`, `gh_cli`, `git_min`, `monitoring`, `node_tools`, `sshd_home`, `stylus_touch_guard`, `thinkpad_tuning`, `touch_device`, `user_tools` and `yazi`.

#### Scenario: Adding an apt-only feature
- **WHEN** a feature needs only apt packages
- **THEN** one entry in `packages_by_feature` is enough

### Requirement: Node tools on every profile
The role `node_tools` SHALL run without `become` on every profile, containers included. It SHALL install a pinned NVM and Node LTS as user-local tools and SHALL keep an existing NVM default with Node 22 or newer. Bash and zsh SHALL load NVM.

#### Scenario: Existing Node 22 default
- **WHEN** NVM already has a default Node version of 22 or newer
- **THEN** that default is kept

### Requirement: LLM CLI features
The features `claude-code` and `copilot-cli` SHALL install those CLIs. Private profiles SHALL default to Claude Code, `work-machine` SHALL default to both, and containers SHALL default to neither, so that container CLIs are opt-in.

#### Scenario: Container profile
- **WHEN** a host has the `container` profile and no LLM feature is selected
- **THEN** no LLM CLI is installed

### Requirement: OpenSpec installed with an LLM CLI
OpenSpec SHALL be installed automatically once an LLM CLI is selected or already installed.

#### Scenario: Work machine
- **WHEN** `node_tools` runs on a host with `copilot-cli` selected
- **THEN** OpenSpec is installed

### Requirement: Existing installations are preserved
Provisioning SHALL preserve existing installations where possible: `gh` and `az` with their authentication, an existing Docker provider, an installed `yazi`, and existing LLM CLIs.

#### Scenario: Existing gh login
- **WHEN** `gh` is already installed and authenticated
- **THEN** provisioning does not replace it or remove the login

### Requirement: Root is needed for system roles
The workstation playbook SHALL need root through `become`. On managed work machines that do not allow it, dotfiles and env management SHALL still be usable without the system roles.

#### Scenario: Host without root
- **WHEN** a work machine cannot become root
- **THEN** the dotfiles and env management still run and the system roles are not applied

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
