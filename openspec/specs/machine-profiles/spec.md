# machine-profiles Specification

## Purpose
Defines machine profiles and how a host gets its profile.

## Requirements

### Requirement: Context and device per host
Every host SHALL have a context (`private` or `work`) and a device (`desktop`, `server` or `container`); together with its features they form the host config. A container SHALL have no context unless an override sets one. The host config SHALL be versioned in `machine/hosts/<hostname>.yml`, the only source of it.

#### Scenario: Looking up a host
- **WHEN** a host is set up
- **THEN** its context, device and features are read from its `machine/hosts/<hostname>.yml`, with unset features taken from the feature table defaults

#### Scenario: Setup changes the selection
- **WHEN** `machine setup` runs, also with `--yes`, and the chosen context, device or features differ from `machine/hosts/<hostname>.yml`
- **THEN** the repository file is updated without a question and setup offers to commit it

### Requirement: Applied host config
`machine` SHALL keep the last applied host config in its state directory (`~/.local/share/machine/applied-host.yml`): it is what a failed apply restores, what the shell reads at start, and the host config of hosts without a repository file.

#### Scenario: Container
- **WHEN** `machine setup` runs with the device `container`
- **THEN** no repository file is written and the applied host config holds the selection

### Requirement: Default context and device on setup
When setup has to choose, the device SHALL be the first match of: `container` in Docker (`/.dockerenv` or `MACHINE_IN_DOCKER=1`) unless `MACHINE_DEVICE_OVERRIDE` names one; the saved value; an inherited `MACHINE_DEVICE`; `desktop` when the system boots into a graphical target; otherwise `server`. The context SHALL be the first match of: none in Docker unless `MACHINE_CONTEXT_OVERRIDE` names one; the saved value; an inherited `MACHINE_CONTEXT`; `work` for a company user ID; otherwise `private`.

#### Scenario: Container with a saved host profile
- **WHEN** the host's applied host config is visible in a container because the home directory is shared
- **THEN** the device is `container` and there is no context

#### Scenario: Container with an override
- **WHEN** `MACHINE_CONTEXT_OVERRIDE=work` and `MACHINE_DEVICE_OVERRIDE=desktop` are set in a container
- **THEN** the context is `work` and the device is `desktop`

#### Scenario: Company user ID on a fresh host
- **WHEN** nothing is saved or inherited, the host is not in Docker and the user name matches `^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$`
- **THEN** the default context is `work`

#### Scenario: Plain user name on a fresh host
- **WHEN** none of the earlier checks match and the user name does not match the company format
- **THEN** the default context is `private`

#### Scenario: Fresh host without a graphical target
- **WHEN** nothing is saved or inherited and the system boots into a non-graphical target
- **THEN** the default device is `server`

### Requirement: Context and device exported to the shell
In the shell, `machine-profile.sh` SHALL export `MACHINE_CONTEXT` and `MACHINE_DEVICE` using the same Docker rule and overrides as the `machine` CLI; it SHALL be shared by zsh and bash. `MACHINE_CONTEXT` SHALL be unset when the host has no context.

#### Scenario: Shell start
- **WHEN** an interactive zsh or bash starts on a private laptop
- **THEN** `MACHINE_CONTEXT` is `private` and `MACHINE_DEVICE` is `desktop`

#### Scenario: Shell in a container with a shared home
- **WHEN** a shell starts in a container whose home contains a host's applied host config
- **THEN** `MACHINE_DEVICE` is `container` and `MACHINE_CONTEXT` is unset

### Requirement: Host-config changes from the repository are applied with a notice
`machine update` and `machine apply` SHALL take `machine/hosts/<hostname>.yml` over the applied host config without asking, and SHALL print the changed context or device, the added and removed features and the changed `ssh_allow_from` entries when it changes. `machine update --check` SHALL list an incoming change of the host's file before it is applied.

#### Scenario: Feature added on another host
- **WHEN** another host commits `thunderbird` to this host's file and this host runs `machine update`
- **THEN** the update prints `+ thunderbird`, applies the feature and asks nothing

#### Scenario: Local copy edited by hand
- **WHEN** the applied host config was edited by hand and `machine update` runs
- **THEN** the repository file wins and the printed changes show what was undone

#### Scenario: Check before the update
- **WHEN** an incoming commit changes this host's file and the user runs `machine update --check`
- **THEN** the planned host-config changes are listed

### Requirement: Old local profile is taken over
When `~/.config/machine/profile.yml` exists and no applied host config does, `machine` SHALL take it over once into the state directory and remove the old file. A former `profile:` key SHALL be mapped: `work-machine` to work and desktop; `home-laptop` to private and desktop; `home-server`, `rpi` and `rpi-zero` to private and server; `container` to the container device.

#### Scenario: Host not yet updated
- **WHEN** a host still has `~/.config/machine/profile.yml` with `profile: home-server` and `machine update` runs
- **THEN** the host is treated as private and server, the applied host config is written in the state directory and the old file is removed

### Requirement: Ansible can be switched off per host
A host config with `ansible: false` SHALL make `machine setup`, `apply` and `update` skip Ansible and report that it was skipped; dotfiles, user-space tools and secrets SHALL still be applied. Without the setting, Ansible SHALL run with root.

#### Scenario: Managed host without root
- **WHEN** a host config has `ansible: false` and `machine update` runs
- **THEN** the dotfile groups and user-space tools are applied, Ansible does not run, and no system update is reported as pending

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

### Requirement: First setup keeps the allowed SSH hosts
Without an applied host config, `machine setup` SHALL use the `ssh_allow_from` entries of the host's repository config as the current selection: offered preselected on a terminal and kept unchanged without one.

#### Scenario: Non-interactive first setup
- **WHEN** `machine setup --yes` runs on a fresh host whose repository config lists `ssh_allow_from: [laptop1]`
- **THEN** the written host config still lists `laptop1`
