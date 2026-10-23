## MODIFIED Requirements

### Requirement: Handoff health check
Before handing an interactive bash session over to zsh, the system SHALL verify that zsh is executable, that `~/.zshrc` and the zsh loader are present and readable, and that a login interactive zsh starts without error output. The trial start SHALL also run the deferred plugin part, so that an error in a deferred plugin is detected.

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

#### Scenario: Deferred plugin fails
- **WHEN** a deferred plugin writes an error or does not finish loading during the trial start
- **THEN** it is treated as a failure, the session stays in bash, and the diagnostic names the incomplete load

#### Scenario: Everything healthy
- **WHEN** all checks pass
- **THEN** the system hands over to zsh as before

### Requirement: Cache invalidation
The system SHALL discard the cached outcome and re-run the checks when any of the following happens:
- the zsh binary path or version changes;
- `~/.zshenv`, `~/.zshrc`, `~/.zsh/config/*.zsh`, the zsh plugin list, `~/.zsh/machine-profile.sh` or `~/.preferred-shell` changes;
- the dotfiles are updated.

#### Scenario: Config edited after failure
- **WHEN** a zsh config file is modified after a cached failure
- **THEN** the next interactive bash start re-runs the checks

#### Scenario: Plugin list edited
- **WHEN** the zsh plugin list is modified after a cached pass
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
