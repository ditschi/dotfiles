## MODIFIED Requirements

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
