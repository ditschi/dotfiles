# work-private-separation Specification

## Purpose
Defines how work-specific behaviour, secrets, Git identity and SSH keys are kept apart from private ones.

## Requirements

### Requirement: Work detection in the shell
The shell SHALL set `WORK_SETUP=true` when the profile is `work-machine`, or when the user name is a company user ID and the profile is not `container`.

#### Scenario: Work host
- **WHEN** a shell starts on a `work-machine` host
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Private host with a company user ID
- **WHEN** a shell starts for a company user ID on a host with another profile that is not `container`
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Container with a company user ID
- **WHEN** a shell starts for a company user ID in a container with the `container` profile
- **THEN** `WORK_SETUP` is not set

### Requirement: Work modules only for work
The work modules (`01_work*.zsh`) SHALL belong to a group that only the profile `work-machine` selects, and they SHALL return early unless `WORK_SETUP=true`.

#### Scenario: Private profile
- **WHEN** the dotfile groups are applied for the profile `home-laptop`
- **THEN** no work module is linked

#### Scenario: Work module without work setup
- **WHEN** a linked work module is sourced and `WORK_SETUP` is not `true`
- **THEN** it returns without effect

### Requirement: Work and private stay separate
The separation SHALL also cover the Git default identity (`~/.gitconfig.local`, from the profile), the Bitwarden environment groups (`work` versus `private`, `server` and `iot`) and the SSH key class (`work` versus `home`).

#### Scenario: Private host
- **WHEN** a private host loads secrets
- **THEN** only its own environment groups are queried, never the work group

### Requirement: Shareable repository
The repository SHALL NOT contain secrets or sensitive work details; real work identity, internal endpoints and network details SHALL live in local or private configuration.

#### Scenario: Committing setup logic
- **WHEN** generic setup logic is committed
- **THEN** it contains sanitized examples only, and real values come from local or private configuration
