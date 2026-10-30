# Spec Delta

## MODIFIED Requirements

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
