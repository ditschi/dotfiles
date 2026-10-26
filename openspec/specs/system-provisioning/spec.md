# system-provisioning Specification

## Purpose
Defines how Ansible applies packages, tools and system configuration for a host's features.

## Requirements

### Requirement: Ansible applies the feature list
Packages and system configuration SHALL be applied by Ansible through `machine apply`, `machine setup` and `machine update --system`, driven by the host's feature list.

#### Scenario: Host with a feature
- **WHEN** a host has a feature enabled and `machine apply` runs
- **THEN** the packages and configuration of that feature are applied

### Requirement: Package table
Apt packages per feature SHALL be defined in one table (`packages_by_feature` in `group_vars/all/packages.yml`), so that a new apt-only feature needs a single entry next to its row in the feature table (`group_vars/all/features.yml`).

#### Scenario: Adding an apt-only feature
- **WHEN** a feature needs only apt packages
- **THEN** one entry in `packages_by_feature` and one row in the feature table are enough

### Requirement: Local roles
Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `touch_device`, `lid_switch`, `power_profile_switch`, `battery_charge_limit` and `zram_swap`; model tuning SHALL be a local role per hardware model, such as `thinkpad_l13_yoga_gen2`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

### Requirement: LLM CLI features
The features `claude-code`, `copilot-cli` and `opencode` SHALL install those CLIs, and only a host with the feature SHALL get the CLI. Private hosts SHALL preselect Claude Code and offer Copilot and opencode without preselecting them; work hosts SHALL preselect Claude Code and Copilot; containers SHALL preselect none, so that container CLIs are opt-in.

#### Scenario: Container profile
- **WHEN** a host has the device `container` and no LLM feature is selected
- **THEN** no LLM CLI is installed

#### Scenario: Private host
- **WHEN** a private host takes the feature defaults
- **THEN** `claude-code` is selected and `copilot-cli` and `opencode` are offered but not selected

### Requirement: OpenSpec installed with an LLM CLI
OpenSpec SHALL be installed whenever at least one LLM CLI feature (`claude-code`, `copilot-cli`, `opencode`) is selected, and SHALL NOT be installed otherwise.

#### Scenario: Work machine
- **WHEN** setup runs on a host with `copilot-cli` selected
- **THEN** OpenSpec is installed

#### Scenario: No LLM CLI
- **WHEN** setup runs in a container without any LLM feature
- **THEN** OpenSpec is not installed

### Requirement: Existing installations are preserved
Provisioning SHALL preserve existing installations where possible: `gh` and `az` with their authentication, an existing Docker provider, an installed `yazi`, and existing LLM CLIs.

#### Scenario: Existing gh login
- **WHEN** `gh` is already installed and authenticated
- **THEN** provisioning does not replace it or remove the login

### Requirement: System roles run with root unless switched off
The workstation playbook SHALL need root through `become` and SHALL only apply system packages and system configuration. Root SHALL be assumed on every host; a host whose host config sets `ansible: false` SHALL skip the playbook, while dotfiles, user-space tools and env management still run.

#### Scenario: Host without root
- **WHEN** a host config sets `ansible: false`
- **THEN** the dotfiles, user-space tools and env management still run and the system roles are not applied

#### Scenario: Root not available without the setting
- **WHEN** a host without `ansible: false` cannot become root
- **THEN** the Ansible run fails with a message that names the setting

### Requirement: Collections and Galaxy roles
`ansible.posix` SHALL be the only required collection, and Galaxy roles SHALL NOT be used; thin local roles are used instead.

#### Scenario: Installing requirements
- **WHEN** the Ansible requirements are installed
- **THEN** only `ansible.posix` is installed

### Requirement: etckeeper outside containers
The feature `etckeeper` SHALL be preselected on every host except those with the device `container`.

#### Scenario: Home laptop
- **WHEN** a private desktop takes its feature defaults
- **THEN** `etckeeper` is included
