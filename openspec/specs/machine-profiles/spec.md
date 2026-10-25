# machine-profiles Specification

## Purpose
Defines machine profiles and how a host gets its profile.

## Requirements

### Requirement: One profile per host
Every host SHALL have exactly one profile out of `work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero` and `container`. Feature defaults per profile SHALL live in `ansible/profiles/<profile>.yml`, and the chosen profile and features of a host SHALL be versioned in `machine/hosts/<hostname>.yml`, which SHALL be the only source of the host's profile. `~/.config/machine/profile.yml` SHALL be a copy that `machine` writes from it; it is the applied state and the profile of hosts without a repository file.

#### Scenario: Looking up a host
- **WHEN** a host is set up
- **THEN** its profile and features are read from its `machine/hosts/<hostname>.yml`, with unset features taken from the profile defaults

#### Scenario: Setup changes the selection
- **WHEN** `machine setup` runs, also with `--yes`, and the chosen profile or features differ from `machine/hosts/<hostname>.yml`
- **THEN** the repository file is updated without a question and setup offers to commit it

#### Scenario: Container
- **WHEN** `machine setup` runs with the `container` profile
- **THEN** no repository file is written and the local copy holds the profile

### Requirement: Default profile on setup
When setup has to choose a profile, it SHALL use the first match of: `container` when running in Docker (`/.dockerenv` exists or `MACHINE_IN_DOCKER=1`), unless `MACHINE_PROFILE_OVERRIDE` names a profile, which is then used; the saved local or host profile; an inherited `MACHINE_PROFILE`; `work-machine` when the user name matches the company user ID format (`^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$`); otherwise `home-laptop`.

#### Scenario: Container with a saved host profile
- **WHEN** the host's saved profile is visible in a container because the home directory is shared
- **THEN** the profile is `container`

#### Scenario: Container with an override
- **WHEN** `MACHINE_PROFILE_OVERRIDE=work-machine` is set in a container
- **THEN** the profile is `work-machine`

#### Scenario: Company user ID on a fresh host
- **WHEN** no profile is saved, the host is not in Docker, no `MACHINE_PROFILE` is inherited, and the user name matches the company format
- **THEN** the default profile is `work-machine`

#### Scenario: Plain user name on a fresh host
- **WHEN** none of the earlier checks match and the user name does not match the company format
- **THEN** the default profile is `home-laptop`

### Requirement: Profile exported to the shell
In the shell, `machine-profile.sh` SHALL export `MACHINE_PROFILE` using the same Docker rule and override as the `machine` CLI; it SHALL be shared by zsh and bash.

#### Scenario: Shell start
- **WHEN** an interactive zsh or bash starts
- **THEN** `MACHINE_PROFILE` is set for that shell

#### Scenario: Shell in a container with a shared home
- **WHEN** a shell starts in a container whose home contains a host's saved profile
- **THEN** `MACHINE_PROFILE` is `container`

### Requirement: Profile changes from the repository are applied with a notice
`machine update` and `machine apply` SHALL copy `machine/hosts/<hostname>.yml` over the local copy without asking, and SHALL print the changed profile, the added and removed features and the changed `ssh_allow_from` entries when the copy changes. `machine update --check` SHALL list an incoming change of the host's file before it is applied.

#### Scenario: Feature added on another host
- **WHEN** another host commits `thunderbird` to this host's file and this host runs `machine update`
- **THEN** the update prints `+ thunderbird`, applies the feature and asks nothing

#### Scenario: Local copy edited by hand
- **WHEN** the local copy differs from the repository file and `machine update` runs
- **THEN** the repository file wins and the printed changes show what was undone

#### Scenario: Check before the update
- **WHEN** an incoming commit changes this host's file and the user runs `machine update --check`
- **THEN** the planned profile changes are listed
