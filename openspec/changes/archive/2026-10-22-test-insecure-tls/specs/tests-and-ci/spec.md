## MODIFIED Requirements

### Requirement: Local test commands
The repository SHALL offer `uvx nox` (compile, unit tests, Ansible syntax and lint, Docker smoke), `pytest tests/unit` (CLI logic, git config, host profiles, packages, update and env), Docker integration tests per profile, and APT and Ansible idempotence tests (`-m apt`, `-m apt_gnome`). The Docker tests SHALL support an opt-in `DOTFILES_TEST_INSECURE_TLS=1` that skips TLS verification in the test image and containers only, for hosts that intercept TLS; it is off by default.

#### Scenario: Running the unit tests
- **WHEN** a user runs `pytest tests/unit`
- **THEN** the unit tests run without Docker

#### Scenario: Docker tests on a TLS-intercepting host
- **WHEN** a user runs `DOTFILES_TEST_INSECURE_TLS=1 uvx nox -s docker`
- **THEN** the test image and containers skip TLS verification

#### Scenario: Default verification
- **WHEN** the variable is not set
- **THEN** the test image and containers verify TLS as usual
