# shell-handoff Specification

## Purpose
Defines how an interactive bash session hands over to the preferred shell on hosts where the account's login shell cannot be changed, so that the customised zsh is used where it is available.

## Requirements

### Requirement: Customised zsh is preferred when installed
An interactive top-level bash session SHALL hand over to zsh with the dotfiles customisation when zsh is installed, unless the user has explicitly configured another shell.

#### Scenario: zsh installed, no override
- **WHEN** a user opens an interactive top-level bash session and zsh is installed
- **THEN** the session is replaced by a zsh login shell

#### Scenario: zsh not installed
- **WHEN** a user opens an interactive top-level bash session and zsh is not installed
- **THEN** the session stays in bash

### Requirement: Manually started bash is respected
The handoff SHALL NOT replace a bash session that the user started manually, from another shell or inside another bash, so that the user ends up in bash as asked.

#### Scenario: bash started from another shell
- **WHEN** the user starts bash from another interactive shell (for example zsh)
- **THEN** the session stays in bash

#### Scenario: nested bash
- **WHEN** the user starts bash inside an existing shell level
- **THEN** the session stays in bash

### Requirement: Explicit preferred shell
A valid `~/.preferred-shell` SHALL take precedence over the default handoff: the named shell is used if it is installed, and a value of bash keeps the session in bash.

#### Scenario: preferred shell set and installed
- **WHEN** `~/.preferred-shell` names an installed shell other than bash
- **THEN** the session is replaced by that shell as a login shell, also inside Docker

#### Scenario: preferred shell set to bash
- **WHEN** `~/.preferred-shell` names bash
- **THEN** the session stays in bash

### Requirement: Handoff works without changing the login shell
The handoff SHALL NOT depend on changing the account's login shell. Changing it is possible on private hosts but not on work hosts, where the account is centrally managed.

#### Scenario: Work host without chsh
- **WHEN** the setup is used on a work host whose account is not in the local password database
- **THEN** zsh is reached through the bash handoff

### Requirement: Handoff health check
Before handing an interactive bash session over to zsh, the system SHALL verify that zsh is executable, that `~/.zshrc` and `~/.shell/zsh/init.zsh` are present and readable, and that a login interactive zsh starts without error output. The trial start SHALL also run the deferred plugin part, so that an error in a deferred plugin is detected.

#### Scenario: zsh is not installed
- **WHEN** the handoff is about to run and no zsh executable is found
- **THEN** the session stays in bash and a one-line diagnostic names the missing zsh

#### Scenario: Loader is missing
- **WHEN** `~/.shell/zsh/init.zsh` does not exist
- **THEN** the session stays in bash and the diagnostic names the missing loader

#### Scenario: zsh fails to start
- **WHEN** a trial `zsh -l -i` start exits non-zero or writes to stderr
- **THEN** the session stays in bash and the diagnostic names the startup failure

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
The system SHALL store the check outcome (pass or fail, and the failing check) in a per-user state file and SHALL NOT repeat the checks while the cached outcome is valid.

#### Scenario: Cached pass
- **WHEN** a valid cached pass exists
- **THEN** no trial zsh start is performed and the handoff proceeds

#### Scenario: Cached failure
- **WHEN** a valid cached failure exists
- **THEN** the session stays in bash and the diagnostic is shown again without re-running the trial start

### Requirement: Cache invalidation
The system SHALL discard the cached outcome and re-run checks when the zsh binary path/version, shell preference, zsh entry points/local override, health-check helper, or startup inputs under `~/.shell/common`, `~/.shell/zsh` and `~/.shell/work` change, including the plugin list and file removal/rename. Dotfile updates SHALL invalidate the outcome. Changes to Bash-only modules other than the health-check helper SHALL NOT require a new zsh check.

#### Scenario: Config edited after failure
- **WHEN** a zsh config file is modified after a cached failure
- **THEN** the next interactive bash start re-runs the checks

#### Scenario: Plugin list edited
- **WHEN** `~/.shell/zsh/plugins.txt` is modified after a cached pass
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

#### Scenario: Shared helper changed
- **WHEN** a shared startup helper under `~/.shell/common` changes after a cached outcome
- **THEN** the next eligible Bash handoff re-runs the zsh checks

#### Scenario: Work startup input changed
- **WHEN** a work startup module changes, is removed or is renamed after a cached outcome on a work host
- **THEN** the next eligible Bash handoff re-runs the zsh checks

#### Scenario: Host-local override changed
- **WHEN** `~/.zshrc-local` changes after a cached outcome
- **THEN** the next eligible Bash handoff re-runs the zsh checks

#### Scenario: Health-check implementation changed
- **WHEN** `~/.shell/bash/zsh-health.bash` changes after a cached outcome
- **THEN** the next eligible Bash handoff re-runs the zsh checks

#### Scenario: Bash-only integration changed
- **WHEN** only a Bash editor, history or prompt module changes locally without a dotfile update
- **THEN** that edit alone does not invalidate the zsh health outcome

### Requirement: Health check does not change who is handed over
The health check SHALL run only for sessions that would hand over to zsh anyway, and SHALL NOT change which sessions are handed over.

#### Scenario: Session that stays in bash
- **WHEN** a session would not hand over (nested or manually started bash, non-interactive shell, or an explicit bash preference)
- **THEN** the health check does not run

### Requirement: Fresh hosts are not judged
If the zsh plugin manager or its generated plugin file does not exist, the system SHALL skip the trial start, hand over to zsh and cache no outcome, so that the first start can install the plugins.

#### Scenario: First start on a fresh host
- **WHEN** the handoff runs and antidote or its generated plugin file is not present yet
- **THEN** the session is handed over to zsh and no outcome is cached

#### Scenario: Check resumes after installation
- **WHEN** antidote and its generated plugin file exist on a later start
- **THEN** the health check runs as usual

#### Scenario: Old zinit data only
- **WHEN** a host still has `~/.local/share/zinit` but no antidote
- **THEN** it is treated as a fresh host

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
