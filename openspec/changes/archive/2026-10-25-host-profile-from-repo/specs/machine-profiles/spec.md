# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
