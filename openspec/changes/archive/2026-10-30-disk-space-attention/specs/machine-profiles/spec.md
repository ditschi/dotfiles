# Spec Delta

## ADDED Requirements

### Requirement: Disk space settings in the host config
The host config SHALL accept the optional key `disk_space` (see the capability `disk-space`). Every rewrite of the host config (`machine setup`, `machine host save`, the takeover into the applied host config) SHALL keep it unchanged. A change to `disk_space` in the repository SHALL be taken over into the applied host config like any other host config change.

#### Scenario: Setup keeps the key
- **WHEN** `machine/hosts/ABTVL421.yml` has a `disk_space` entry and `machine setup` rewrites the file with changed features
- **THEN** the `disk_space` entry is still in the file

#### Scenario: Changed thresholds reach the host
- **WHEN** the `disk_space` entry of a host changes in the repository and `machine update` runs on that host
- **THEN** the applied host config holds the new entry and the next check uses it

#### Scenario: Host config without the key
- **WHEN** a host config has no `disk_space`
- **THEN** a rewrite does not add the key, and the defaults apply
