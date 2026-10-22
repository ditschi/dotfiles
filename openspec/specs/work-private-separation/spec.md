# work-private-separation Specification

## Purpose
Defines how work-specific behaviour, secrets, Git identity and SSH keys are kept apart from private ones.

## Requirements

### Requirement: Work detection in the shell
The shell SHALL set `WORK_SETUP=true` when the profile is `work-machine` or the user name is a company user ID.

#### Scenario: Work host
- **WHEN** a shell starts on a `work-machine` host
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Private host with a company user ID
- **WHEN** a shell starts for a company user ID on a host with another profile
- **THEN** `WORK_SETUP` is `true`

### Requirement: Work modules only for work
The work modules (`01_work*.zsh`) SHALL be linked by chezmoi only for profile `work-machine`, and they SHALL return early unless `WORK_SETUP=true`.

#### Scenario: Private profile
- **WHEN** chezmoi applies the profile `home-laptop`
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
