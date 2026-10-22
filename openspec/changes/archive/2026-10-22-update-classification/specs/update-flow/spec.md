## MODIFIED Requirements

### Requirement: Update never discards local work
`machine update` SHALL first run the known local-change resolvers (starting with the relocation of host-only Git settings into local config, and the move of externally managed blocks from `~/.bashrc` into `~/.bashrc-local`). It SHALL fast-forward without touching local changes. It SHALL stop and report that manual attention is needed, and why, only when a locally changed file is also changed by the incoming commits, or when the history has diverged. Local changes that remain without overlap SHALL be reported as a notice and do not block the update. `--force` is only needed when the user wants to override a stop.

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

## ADDED Requirements

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
