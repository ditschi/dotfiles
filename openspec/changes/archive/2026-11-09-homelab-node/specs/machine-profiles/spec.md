# Spec Delta

## ADDED Requirements

### Requirement: Homelab settings in the host config
The host config SHALL accept the optional block `homelab` with the keys `host`, `user`, `clone` and `ci_restrict`. Every rewrite of the host config (`machine setup`, `machine host save`, the takeover into the applied host config) SHALL keep it unchanged, and a change in the repository SHALL reach the applied host config like any other host config change.

#### Scenario: Setup keeps the block
- **WHEN** `machine/hosts/contabo.yml` has `homelab: {user: ditschi}` and `machine setup` rewrites the file with changed features
- **THEN** the `homelab` block is still in the file

#### Scenario: Host config without the block
- **WHEN** a host config has no `homelab` block
- **THEN** a rewrite does not add it

### Requirement: Homelab host name default
Without `homelab.host`, the homelab host name SHALL be the short hostname. It SHALL name the Bitwarden item `homelab-age-<host>`.

#### Scenario: oracle
- **WHEN** the host `privatecloud` sets `homelab.host: oracle`
- **THEN** the item `homelab-age-oracle` is used

#### Scenario: contabo
- **WHEN** the host `contabo` has no `homelab.host`
- **THEN** the item `homelab-age-contabo` is used
