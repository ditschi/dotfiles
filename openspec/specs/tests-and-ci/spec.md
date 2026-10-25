# tests-and-ci Specification

## Purpose
Defines the local test commands, the CI jobs and what is deliberately left out of CI.

## Requirements

### Requirement: Local test commands
The repository SHALL offer `uvx nox` (compile, unit tests, Ansible syntax and lint, Docker smoke), `pytest tests/unit` (CLI logic, git config, host configs, packages, update and env), Docker integration tests per context and device, and APT and Ansible idempotence tests (`-m apt`, `-m apt_gnome`).

#### Scenario: Running the unit tests
- **WHEN** a user runs `pytest tests/unit`
- **THEN** the unit tests run without Docker

#### Scenario: Docker tests on a TLS-intercepting host
- **WHEN** a user runs `DOTFILES_TEST_INSECURE_TLS=1 uvx nox -s docker`
- **THEN** the test image and containers skip TLS verification

#### Scenario: Docker tests on a work machine
- **WHEN** the host is a work machine and the variable is not set
- **THEN** the test image and containers skip TLS verification

#### Scenario: Work machine opts out
- **WHEN** the host is a work machine and `DOTFILES_TEST_INSECURE_TLS=0` is set
- **THEN** the test image and containers verify TLS as usual

#### Scenario: Default verification
- **WHEN** the host is not a work machine and the variable is not set
- **THEN** the test image and containers verify TLS as usual

#### Scenario: Insecure TLS for intercepting hosts
- **WHEN** `DOTFILES_TEST_INSECURE_TLS=1` is set, or the host is a work machine and the variable is unset
- **THEN** the Docker tests skip TLS verification in the test image and containers only

#### Scenario: Explicit override
- **WHEN** `DOTFILES_TEST_INSECURE_TLS` is `0` or `1`
- **THEN** it overrides the default, which is off outside work machines

### Requirement: CI jobs
The CI workflow `verify.yml` SHALL run the unit tests and Ansible syntax on amd64 and arm, a Docker profile matrix, a clean install, APT runs, `pre-commit`, `ansible-lint` and host YAML validation on relevant changes.

#### Scenario: Push with relevant changes
- **WHEN** a push changes files covered by a job
- **THEN** that job runs

### Requirement: Not covered by CI
The following SHALL be deliberately left out of CI: real Raspberry Pi hardware, Kerberos against the work KDC, a Cosmic session, a real `bw login` with 2FA, and a real Influx instance.

#### Scenario: Reviewing CI coverage
- **WHEN** a change touches one of these areas
- **THEN** it is verified manually, not by CI
