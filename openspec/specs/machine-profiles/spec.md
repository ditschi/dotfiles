# machine-profiles Specification

## Purpose
Defines machine profiles and how a host gets its profile.

## Requirements

### Requirement: One profile per host
Every host SHALL have exactly one profile out of `work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero` and `container`. Feature defaults per profile SHALL live in `ansible/profiles/<profile>.yml`, and the chosen profile and features of a host SHALL be versioned in `machine/hosts/<hostname>.yml`.

#### Scenario: Looking up a host
- **WHEN** a host is set up
- **THEN** its profile and features are read from its `machine/hosts/<hostname>.yml`, with unset features taken from the profile defaults

### Requirement: Default profile on setup
When setup has to choose a profile, it SHALL use the first match of: the saved local or host profile; `container` when running in Docker; an inherited `MACHINE_PROFILE`; `work-machine` when the user name matches the company user ID format (`^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$`); otherwise `home-laptop`.

#### Scenario: Company user ID on a fresh host
- **WHEN** no profile is saved, the host is not in Docker, no `MACHINE_PROFILE` is inherited, and the user name matches the company format
- **THEN** the default profile is `work-machine`

#### Scenario: Plain user name on a fresh host
- **WHEN** none of the earlier checks match and the user name does not match the company format
- **THEN** the default profile is `home-laptop`

### Requirement: Profile exported to the shell
In the shell, `machine-profile.sh` SHALL export `MACHINE_PROFILE`; it SHALL be shared by zsh and bash.

#### Scenario: Shell start
- **WHEN** an interactive zsh or bash starts
- **THEN** `MACHINE_PROFILE` is set for that shell
