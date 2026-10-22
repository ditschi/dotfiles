# update-flow Specification

## Purpose
Defines how a user learns about dotfiles updates and how `machine update` applies them.

## Requirements

### Requirement: Update hint at shell start
When the marker file `~/.dotfiles-update-available` exists, a new zsh SHALL print "Hint: Dotfiles update available (run: machine update)". The shell SHALL NOT run the update check itself, so that startup stays fast.

#### Scenario: Update available
- **WHEN** the marker exists and a zsh starts
- **THEN** the hint is printed

#### Scenario: No update
- **WHEN** the marker does not exist
- **THEN** no hint is printed

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host profile and apply the setup, running chezmoi before Ansible. Updates SHALL stay explicit: nothing is applied without the user running the command.

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

### Requirement: Update never discards local work
`machine update` SHALL refuse to run on a checkout with uncommitted changes unless `--force` is given, and SHALL stop with an explanation when the history has diverged.

#### Scenario: Dirty checkout
- **WHEN** the checkout has uncommitted changes and `--force` is not given
- **THEN** the changes are listed and the update stops

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
