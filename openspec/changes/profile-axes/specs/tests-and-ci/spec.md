# Spec Delta

## MODIFIED Requirements

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
