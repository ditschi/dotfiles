# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Container profile inside containers`
- TO: `### Requirement: Container device inside containers`

## MODIFIED Requirements

### Requirement: Work-only launchers
The shell wrappers `sde` and `sdx` SHALL exist only on work setups (`01_work.zsh`), and they SHALL call the shared launcher `~/.local/bin/sde`, which uses Docker Compose with the service `dev-env` by default. They SHALL NOT be provided on private machines.

#### Scenario: Private profile
- **WHEN** a shell starts on a host with the context `private`
- **THEN** the `sde` and `sdx` wrappers are not defined

### Requirement: Container device inside containers
The dotfiles inside these containers SHALL be set up with the device `container` and no context, which installs no systemd units and no prompt configs.

#### Scenario: Extended setup in a container
- **WHEN** the extended setup runs inside a project container
- **THEN** `machine` runs with the device `container` and without a context
