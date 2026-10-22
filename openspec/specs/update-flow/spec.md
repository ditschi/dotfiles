# update-flow Specification

## Purpose
Defines how a user learns about dotfiles updates and how `machine update` applies them.

## Requirements

### Requirement: Update hint at shell start
When the marker file `~/.dotfiles-update-available` exists, a new interactive zsh or bash SHALL print "Hint: Dotfiles update available (run: machine update)". The shell SHALL NOT run the update check itself, so that startup stays fast.

#### Scenario: Update available
- **WHEN** the marker exists and a zsh starts
- **THEN** the hint is printed

#### Scenario: Update available in bash
- **WHEN** the marker exists and an interactive bash starts and stays in bash
- **THEN** the hint is printed once

#### Scenario: No update
- **WHEN** the marker does not exist
- **THEN** no hint is printed

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host profile and apply the setup, running chezmoi before Ansible. Updates SHALL stay explicit: nothing is applied without the user running the command.

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

### Requirement: Update never discards local work
`machine update` SHALL first run the known local-change resolvers (host-only Git settings into local config, externally managed `~/.bashrc` blocks into `~/.bashrc-local`), then fast-forward without touching local changes. It SHALL stop and report why only when a locally changed file is also changed upstream or the history diverged. Other local changes SHALL be a notice. `--force` overrides a stop.

#### Scenario: Only expected local changes
- **WHEN** the only local changes are ones a resolver moves into local config
- **THEN** the resolver runs and the update continues

#### Scenario: Dirty checkout
- **WHEN** a locally changed file is also changed by the incoming commits
- **THEN** the files are listed, the reason is reported and the update stops

#### Scenario: Unrelated local change
- **WHEN** a local change remains that the incoming commits do not touch
- **THEN** the update runs, the local change is kept and reported as a notice

#### Scenario: Diverged history
- **WHEN** a fast-forward is not possible
- **THEN** the update stops and nothing is overwritten

### Requirement: Shell helpers
`dotfiles-update` and `update-dotfiles` SHALL delegate to `machine update`. `dotfiles-setup` and `machine-setup` SHALL run `./bootstrap`.

#### Scenario: Running the helper
- **WHEN** a user runs `update-dotfiles`
- **THEN** `machine update` runs

### Requirement: No layout migration
`machine setup` and `machine update` SHALL NOT check for or migrate the old root layout, and the `machine` CLI SHALL NOT provide `migrate` or `rollback` subcommands.

#### Scenario: Update on a migrated host
- **WHEN** a user runs `machine update` on a host with the chezmoi layout
- **THEN** the update runs without any layout check

#### Scenario: Removed subcommands
- **WHEN** a user runs `machine migrate` or `machine rollback`
- **THEN** the CLI reports an unknown command

### Requirement: Targeted update
`machine update` SHALL determine from the incoming changes which steps are needed and run only those: added, removed or renamed home files and `.chezmoiignore` need `chezmoi apply`; changes to the content of existing home files need only a shell refresh; changes to `ansible/**` or packages need the system step; a changed host profile needs the profile apply; changes to `machine/` and the CLI need nothing extra.

#### Scenario: Only a shell file changed
- **WHEN** the incoming changes touch only the content of existing shell configuration files
- **THEN** neither `chezmoi apply` nor the system (Ansible) step runs

### Requirement: Read-only update check
`machine update --check` SHALL show the changed areas, the steps that would run, the local changes and the blockers without changing anything, and SHALL offer `--json` for the background job. `machine status` SHALL use the same result.

#### Scenario: Checking before updating
- **WHEN** a user runs `machine update --check`
- **THEN** nothing is changed and the needed steps and blockers are shown

### Requirement: One update at a time
Background and manual updates SHALL share a lock so that they cannot run at once, and `machine update` SHALL ensure that the update-check timer is enabled.

#### Scenario: Manual update during a background update
- **WHEN** a manual update starts while a background update runs
- **THEN** it waits or reports that an update is already running
