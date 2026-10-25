# Spec Delta

## MODIFIED Requirements

### Requirement: Host behaviour inside the container
The container SHALL use the host's distribution and version as base image, and the context and device of `machine` inside SHALL default to the host's applied host config, so that commands behave as on the host and not as in a project container. `--context` and `--device` SHALL override them; an empty device SHALL use the container device.

#### Scenario: Default profile
- **WHEN** the host's applied host config names context `private` and device `desktop`
- **THEN** `machine` and the shells inside use `private` and `desktop`

#### Scenario: Rootless and rootful Docker
- **WHEN** the Docker daemon runs rootless or rootful
- **THEN** files in the home are owned by the user inside and `sudo` works without a password in both cases
