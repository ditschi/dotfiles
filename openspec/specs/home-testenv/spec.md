# home-testenv Specification

## Purpose
Defines `machine testenv`, which runs `machine` commands in a container against the real home behind a throwaway copy-on-write layer, so that updates and setup can be tried on a host's real state without changing it.

## Requirements

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
The container SHALL use the host's distribution and version as base image, and the context and device of `machine` inside SHALL default to the host's applied host config, so that commands behave as on the host and not as in a project container. `--context` and `--device` SHALL override them; an empty device SHALL use the container device.

#### Scenario: Default profile
- **WHEN** the host's applied host config names context `private` and device `desktop`
- **THEN** `machine` and the shells inside use `private` and `desktop`

#### Scenario: Rootless and rootful Docker
- **WHEN** the Docker daemon runs rootless or rootful
- **THEN** files in the home are owned by the user inside and `sudo` works without a password in both cases

### Requirement: Throwaway layer
All changes made inside SHALL be discarded when the container exits; every run SHALL start from the current state of the host home. The testenv SHALL offer no options to keep, list or compare runs.

#### Scenario: Second run
- **WHEN** a user runs `machine testenv -- machine update` and then `machine testenv`
- **THEN** the second run sees the home as it is on the host, without the changes of the first run
