# Spec Delta

## ADDED Requirements

### Requirement: First setup keeps the allowed SSH hosts
Without an applied host config, `machine setup` SHALL use the `ssh_allow_from` entries of the host's repository config as the current selection: offered preselected on a terminal and kept unchanged without one.

#### Scenario: Non-interactive first setup
- **WHEN** `machine setup --yes` runs on a fresh host whose repository config lists `ssh_allow_from: [laptop1]`
- **THEN** the written host config still lists `laptop1`
