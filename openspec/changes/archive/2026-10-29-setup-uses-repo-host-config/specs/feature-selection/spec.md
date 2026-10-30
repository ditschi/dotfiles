# Spec Delta

## MODIFIED Requirements

### Requirement: Menu shows only allowed features
The feature menu of `machine setup` SHALL list only the features that are not excluded for the host, with the preselected ones marked. Features the host already has SHALL stay selected. Without an applied host config, the features in the host's repository config (`machine/hosts/<hostname>.yml`) SHALL count as the features the host has, when its context and device match the ones chosen in setup.

#### Scenario: Private host menu
- **WHEN** `machine setup` shows the feature menu on a private host
- **THEN** `kerberos` and `azure-cli` are not listed

#### Scenario: First setup with a repository host config
- **WHEN** `machine setup` runs on a host without an applied host config and `machine/hosts/<hostname>.yml` lists the same context and device without `monitoring`
- **THEN** the features of that file are preselected, `monitoring` is not, and the file is written back without `monitoring`

#### Scenario: Repository host config for another device
- **WHEN** the repository host config names device `desktop` and setup chooses `server`
- **THEN** the defaults for a private server are preselected
