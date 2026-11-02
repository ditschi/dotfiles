# Spec Delta

## MODIFIED Requirements

### Requirement: Slow or hanging trial start is inconclusive
The trial start SHALL be aborted after a generous timeout used only as a hang guard. A timeout SHALL NOT be cached as a failure: the session stays in bash for that start and the check runs again on the next start. Aborting the trial SHALL end every process the trial started that did not detach itself, and the user SHALL be able to abort it early with Ctrl-C.

#### Scenario: Trial start exceeds the timeout
- **WHEN** the trial start does not finish within the timeout
- **THEN** it is aborted, nothing is cached, and the session stays in bash

#### Scenario: Process started by the trial outlives zsh
- **WHEN** the trial zsh starts a process that keeps running, and the trial times out
- **THEN** that process is ended together with the trial, unless it detached itself as a daemon (which has no terminal)

#### Scenario: User interrupts the trial
- **WHEN** the user presses Ctrl-C while the trial start runs
- **THEN** the trial and everything it started are ended, nothing is cached, the session stays in bash with a usable prompt, and the diagnostic says the check was interrupted

### Requirement: The check never blocks the user
The check MUST NOT prompt or require root. The trial start MUST NOT read from the user's terminal, so that a startup step waiting for terminal input cannot take keystrokes meant for the shell.

#### Scenario: Check runs on any host
- **WHEN** the check runs on a host without root rights
- **THEN** it completes without prompting

#### Scenario: Startup step waits for terminal input
- **WHEN** a zsh startup step (for example a system login hook running sudo) tries to read from the terminal during the trial
- **THEN** it cannot read the user's terminal, the check ends at the latest at the timeout, and everything the user types afterwards reaches the shell
