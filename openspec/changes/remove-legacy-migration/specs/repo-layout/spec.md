## ADDED Requirements

### Requirement: Single entry point
`./bootstrap` SHALL be the single entry point for a new host, and the repository SHALL NOT ship an `install.py` wrapper. The extended mode of the project container launcher SHALL run `./bootstrap` inside the container.

#### Scenario: New host
- **WHEN** a user runs `./bootstrap` on a new host
- **THEN** `uv` is installed if missing and `machine setup` runs

#### Scenario: Extended project container
- **WHEN** `sdx` starts a project container
- **THEN** the launcher runs `./bootstrap --profile container --yes --no-become` from the mounted dotfiles checkout
