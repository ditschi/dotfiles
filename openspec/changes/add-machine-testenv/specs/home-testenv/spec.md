# Spec Delta

## ADDED Requirements

### Requirement: Run against the real home without changing it
`machine testenv` SHALL run a command, or an interactive login shell when none is given, in a container that sees the invoking user's home at the same path, user name and host name as on the host. The host home SHALL be mounted read-only; every change made inside SHALL go to a separate layer. The exit code SHALL be the command's exit code.

#### Scenario: Testing an update
- **WHEN** a user runs `machine testenv -- 'machine update && machine'`
- **THEN** both commands run against the current state of the home and the exit code of the command line is returned
- **AND** no file in the host home changes

#### Scenario: Checkout as it is
- **WHEN** the host checkout `~/dotfiles` is on a branch with local changes
- **THEN** the container shows the same branch and the same local changes, and only the command under test changes them

#### Scenario: Interactive shell
- **WHEN** a user runs `machine testenv` on a terminal
- **THEN** a login shell of the user's shell starts inside the container in the home directory

#### Scenario: Command tries to write to the host home
- **WHEN** a command inside, also through `sudo`, tries to write to or remount the read-only host home
- **THEN** the write fails and the host home is unchanged

### Requirement: Runs without the installed CLI
The testenv SHALL use only the Python standard library and SHALL be runnable directly from a checkout as `python3 machine_cli/testenv.py`, with the same options as `machine testenv`.

#### Scenario: Installed machine CLI is broken
- **WHEN** the `machine` command of a host fails to start
- **THEN** `python3 machine_cli/testenv.py -- COMMAND` from any checkout still works

### Requirement: Host behaviour inside the container
The container SHALL use the host's distribution and version as base image, and the `machine` profile inside SHALL default to the host's saved profile, so that commands behave as on the host and not as in a project container. `--profile` SHALL override it; an empty value SHALL use the container profile.

#### Scenario: Default profile
- **WHEN** the host's `~/.config/machine/profile.yml` names `home-laptop`
- **THEN** `machine` and the shells inside use `home-laptop`

#### Scenario: Rootless and rootful Docker
- **WHEN** the Docker daemon runs rootless or rootful
- **THEN** files in the home are owned by the user inside and `sudo` works without a password in both cases

### Requirement: Inspecting changes
`--diff` SHALL list the files the command added, changed or deleted in home after it finished, with high-volume tool and cache directories summarised as counts. `--keep NAME` SHALL keep the change layer in a named volume, so a later `machine testenv --keep NAME` continues from it; `--reset` SHALL discard it first, and `--list` SHALL show the kept environments. Without `--keep` the layer SHALL be removed when the container exits.

#### Scenario: Listing changes
- **WHEN** a user runs `machine testenv --diff -- machine setup --yes`
- **THEN** the changed files in home are printed after the command, with caches and tool installs as counts

#### Scenario: Re-entering a kept environment
- **WHEN** a user ran `machine testenv --keep mise -- machine setup --yes` and later runs `machine testenv --keep mise`
- **THEN** the shell sees the home as the first run left it
