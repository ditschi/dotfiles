## MODIFIED Requirements

### Requirement: Local test commands
The repository SHALL offer `uvx nox` (compile, unit tests, Ansible syntax and lint, Docker smoke), `pytest tests/unit` (CLI logic, git config, host profiles, packages, update and env), Docker integration tests per profile, and APT and Ansible idempotence tests (`-m apt`, `-m apt_gnome`). The Docker tests SHALL support `DOTFILES_TEST_INSECURE_TLS=1`, which skips TLS verification in the test image and containers only, for hosts that intercept TLS. It SHALL be on by default on work machines and off by default elsewhere; an explicit `0` or `1` overrides the default.

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
