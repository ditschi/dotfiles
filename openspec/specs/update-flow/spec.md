# update-flow Specification

## Purpose
Defines how a user learns about dotfiles updates and how `machine update` applies them.

## Requirements

### Requirement: Update hint at shell start
Interactive zsh and bash SHALL show the update state as a persistent prompt segment: update available, updated and shell reload needed, or needs attention. A shell started after the update was applied SHALL show nothing. At shell start a one-line message SHALL be printed only for needs-attention. The segment SHOULD follow state changes in an open shell, re-evaluated after each command without reloading the shell, as long as this stays lightweight and the prompt stays fast. The shell SHALL NOT run the update check itself, so that startup stays fast.

#### Scenario: Update available
- **WHEN** an update is pending and not applied automatically and a zsh starts
- **THEN** the prompt segment shows that an update is available and no text is printed at shell start

#### Scenario: Update available in bash
- **WHEN** an update is pending and not applied automatically and an interactive bash starts and stays in bash
- **THEN** the prompt segment shows that an update is available

#### Scenario: Shell older than the applied update
- **WHEN** an update was applied after the shell started
- **THEN** the prompt segment tells the user to reload the shell

#### Scenario: Needs attention
- **WHEN** the update needs manual checking
- **THEN** the prompt segment shows it and a one-line message is printed at shell start

#### Scenario: No update
- **WHEN** no update is pending and the shell is current
- **THEN** nothing is shown

#### Scenario: State changes in an open shell
- **WHEN** the update state changes while a shell is open
- **THEN** the prompt segment shows the new state after the next command

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host profile and apply the setup, running chezmoi before Ansible. System changes and host-profile changes SHALL stay explicit: they are not applied without the user running the command. Changes that only touch home files MAY be applied automatically in the background when the checkout has no local changes after the resolvers.

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

#### Scenario: Home-only change, clean checkout
- **WHEN** the background job finds only home-file changes and the checkout has no local changes
- **THEN** the changes are pulled and applied and the state tells the user to reload the shell

#### Scenario: System change pending
- **WHEN** the incoming changes include a system or host-profile change
- **THEN** nothing at or after the first such commit is applied in the background and the state shows that an update is available

#### Scenario: Home changes before a system change
- **WHEN** the incoming commits are home-only up to a commit that touches `ansible/**`, packages or the host profile
- **THEN** the checkout is fast-forwarded to just before that commit and applied, and the remaining commits stay pending for a manual `machine update`

#### Scenario: Blocked automatic update
- **WHEN** local changes remain after the resolvers
- **THEN** nothing is applied and the state is needs-attention with the reason

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
