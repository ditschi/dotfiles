# Spec Delta

## Purpose

Defines how a new host reaches a working setup from a checkout with no prerequisites except a shell and network access.

## ADDED Requirements

### Requirement: Self-contained bootstrap
The bootstrap script SHALL install `uv` when it is missing and then run `machine setup`, so that no other tooling has to be prepared by hand.

#### Scenario: uv missing
- **WHEN** bootstrap runs and `uv` is not installed
- **THEN** `uv` is installed for the user and `machine setup` runs

#### Scenario: uv present
- **WHEN** bootstrap runs and `uv` is installed
- **THEN** `machine setup` runs without reinstalling `uv`

### Requirement: machine runs through uv
The `machine` command SHALL be a script run by `uv` with its dependencies declared in the script, for Python 3.11 to 3.13.

#### Scenario: Running machine
- **WHEN** a user runs `machine`
- **THEN** `uv` provides an environment with the declared dependencies and the command starts
