## ADDED Requirements

### Requirement: Handoff health check
Before handing an interactive bash session over to zsh, the system SHALL verify that zsh is executable, that `~/.zshrc` and the zsh loader are present and readable, and that a login interactive zsh starts without error output.

#### Scenario: zsh is not installed
- **WHEN** the handoff is about to run and no zsh executable is found
- **THEN** the session stays in bash and a one-line diagnostic names the missing zsh

#### Scenario: Loader is missing
- **WHEN** `~/.zsh/config/00_LOADER.zsh` does not exist
- **THEN** the session stays in bash and the diagnostic names the missing loader

#### Scenario: zsh fails to start
- **WHEN** a trial `zsh -l -i` start exits non-zero or writes to stderr
- **THEN** the session stays in bash and the diagnostic names the startup failure

#### Scenario: Plain or partially loaded zsh
- **WHEN** zsh starts but the dotfiles config did not load completely (for example the loader or theme/plugin setup aborted)
- **THEN** it is treated as a failure, the session stays in bash, and the diagnostic names the incomplete load

#### Scenario: Everything healthy
- **WHEN** all checks pass
- **THEN** the system hands over to zsh as before

### Requirement: Cached result
The system SHALL store the check outcome (pass or fail, and the failing check) in a per-user state file and SHALL NOT repeat the checks while the cached outcome is valid.

#### Scenario: Cached pass
- **WHEN** a valid cached pass exists
- **THEN** no trial zsh start is performed and the handoff proceeds

#### Scenario: Cached failure
- **WHEN** a valid cached failure exists
- **THEN** the session stays in bash and the diagnostic is shown again without re-running the trial start

### Requirement: Cache invalidation
The system SHALL discard the cached outcome and re-run the checks when the zsh binary path or version changes, when `~/.zshrc`, `~/.zsh/config/*.zsh`, `~/.zsh/machine-profile.sh` or `~/.preferred-shell` change, or when the dotfiles are updated.

#### Scenario: Config edited after failure
- **WHEN** a zsh config file is modified after a cached failure
- **THEN** the next interactive bash start re-runs the checks

#### Scenario: Config file removed or renamed
- **WHEN** a zsh config file is removed or renamed after a cached pass
- **THEN** the next interactive bash start re-runs the checks

#### Scenario: zsh upgraded
- **WHEN** the zsh version differs from the cached one
- **THEN** the checks are re-run

#### Scenario: Manual reset
- **WHEN** the user runs the documented reset command
- **THEN** the cache is removed and the next start re-runs the checks

### Requirement: Health check does not change who is handed over
The health check SHALL run only for sessions that would hand over to zsh anyway, and SHALL NOT change which sessions are handed over.

#### Scenario: Session that stays in bash
- **WHEN** a session would not hand over (nested or manually started bash, non-interactive shell, or an explicit bash preference)
- **THEN** the health check does not run

### Requirement: Fresh hosts are not judged
If the zinit installation directory does not exist, the system SHALL skip the trial start, hand over to zsh and cache no outcome, so that the first start can install the plugins.

#### Scenario: First start on a fresh host
- **WHEN** the handoff runs and zinit is not installed yet
- **THEN** the session is handed over to zsh and no outcome is cached

#### Scenario: Check resumes after installation
- **WHEN** zinit is installed on a later start
- **THEN** the health check runs as usual

### Requirement: Slow or hanging trial start is inconclusive
The trial start SHALL be aborted after a generous timeout used only as a hang guard. A timeout SHALL NOT be cached as a failure: the session stays in bash for that start and the check runs again on the next start.

#### Scenario: Trial start exceeds the timeout
- **WHEN** the trial start does not finish within the timeout
- **THEN** it is aborted, nothing is cached, and the session stays in bash

### Requirement: The check never blocks the user
The check MUST NOT prompt or require root.

#### Scenario: Check runs on any host
- **WHEN** the check runs on a host without root rights
- **THEN** it completes without prompting
