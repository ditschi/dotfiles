# Spec Delta

## MODIFIED Requirements

### Requirement: Handoff health check
Before handing an interactive bash session over to zsh, the system SHALL verify that zsh is executable, that `~/.zshrc` and `~/.shell/zsh/init.zsh` are present and readable, and that a strict trial start, a login interactive zsh that skips the global startup files except `/etc/zsh/zshenv` (`zsh -l -i +o GLOBAL_RCS`), starts without error output. The trial start SHALL also run the deferred plugin part, so that an error in a deferred plugin is detected.

#### Scenario: zsh is not installed
- **WHEN** the handoff is about to run and no zsh executable is found
- **THEN** the session stays in bash and a one-line diagnostic names the missing zsh

#### Scenario: Loader is missing
- **WHEN** `~/.shell/zsh/init.zsh` does not exist
- **THEN** the session stays in bash and the diagnostic names the missing loader

#### Scenario: zsh fails to start
- **WHEN** the strict trial start exits non-zero or writes to stderr
- **THEN** the session stays in bash and the diagnostic names the startup failure

#### Scenario: Dotfile writes to stderr while the config loads
- **WHEN** a dotfile startup file writes to stderr during the strict trial start, for example an unguarded `. "$HOME/.cargo/env"` on a host without cargo, and the config still loads completely
- **THEN** it is treated as a failure, the session stays in bash, and the diagnostic names the error output

#### Scenario: System zshenv writes to stderr
- **WHEN** `/etc/zsh/zshenv` writes to stderr
- **THEN** the strict trial start sees that output too and it is treated as a failure, because zsh always reads that file

#### Scenario: Plain or partially loaded zsh
- **WHEN** zsh starts but the dotfiles config did not load completely (for example the loader or theme/plugin setup aborted)
- **THEN** it is treated as a failure, the session stays in bash, and the diagnostic names the incomplete load

#### Scenario: Deferred plugin fails
- **WHEN** a deferred plugin writes an error or does not finish loading during the trial start
- **THEN** it is treated as a failure, the session stays in bash, and the diagnostic names the incomplete load

#### Scenario: Everything healthy
- **WHEN** all checks pass
- **THEN** the system hands over to zsh as before

### Requirement: Cached result
The system SHALL store the check outcome (pass or fail, the failing check, and the warning of a pass) in a per-user state file and SHALL NOT repeat the checks while the cached outcome is valid.

#### Scenario: Cached pass
- **WHEN** a valid cached pass exists
- **THEN** no trial zsh start is performed and the handoff proceeds

#### Scenario: Cached failure
- **WHEN** a valid cached failure exists
- **THEN** the session stays in bash and the diagnostic is shown again without re-running the trial start

#### Scenario: Cached pass with a warning
- **WHEN** a valid cached pass with a warning exists
- **THEN** no trial zsh start is performed, the handoff proceeds and the warning is not shown again

## ADDED Requirements

### Requirement: Full trial start with the system startup files
After the strict trial start passed, the system SHALL run a second trial start as a login interactive zsh with all startup files (`zsh -l -i`). A non-zero exit, an incomplete load, a timeout or an interrupt of this run SHALL be handled as for the strict run. When the strict run failed, the full run SHALL NOT be performed.

#### Scenario: Full run fails to start
- **WHEN** the strict trial start passes and the full trial start exits non-zero or does not load the config completely
- **THEN** it is treated as a failure, the session stays in bash, and the diagnostic names the failure of the full run

#### Scenario: Full run times out
- **WHEN** the strict trial start passes and the full trial start exceeds the timeout
- **THEN** it is aborted, nothing is cached, and the session stays in bash

#### Scenario: Strict run fails
- **WHEN** the strict trial start fails
- **THEN** no full trial start is performed and the failure of the strict run is reported

### Requirement: Error output of the full start is a warning
Error output of the full trial start SHALL NOT count as a failure. When the full trial start otherwise passes but wrote to stderr, the outcome SHALL be a pass, the session SHALL be handed over to zsh, and a one-line warning with the first line of that output SHALL be shown where the check ran.

#### Scenario: System login hook prints a message
- **WHEN** a global startup file other than `/etc/zsh/zshenv` (for example a login hook added by an administrator) prints a line to stderr, the strict trial start passes and the full trial start loads the config completely
- **THEN** the session is handed over to zsh, a one-line warning shows the message, and the outcome is cached as a pass

#### Scenario: Manual recheck shows the warning
- **WHEN** the user runs `zsh-recheck` and the full trial start writes to stderr
- **THEN** the command reports that the check passed and shows the warning
