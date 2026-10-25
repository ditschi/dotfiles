# Spec Delta

## ADDED Requirements

### Requirement: Thunderbird feature
The feature `thunderbird` SHALL install Thunderbird and SHALL be on by default only for the `home-laptop` profile.

#### Scenario: New private laptop
- **WHEN** a host is set up with the `home-laptop` profile defaults
- **THEN** the feature `thunderbird` is selected and `machine apply` installs Thunderbird

#### Scenario: Other profiles
- **WHEN** a host with another profile uses its defaults
- **THEN** the feature is not selected

### Requirement: CLI and bridge from mise
`thunderbird-cli` and `thunderbird-cli-bridge` SHALL be user tools of a dotfile group `thunderbird` that only the `thunderbird` feature selects.

#### Scenario: Host with the feature
- **WHEN** `machine setup` runs with the feature
- **THEN** `tb` and `tb-bridge` are on `PATH`

#### Scenario: Host without the feature
- **WHEN** the feature is not selected
- **THEN** neither tool is installed

### Requirement: Extension only by hand
The bridge extension SHALL NOT be installed automatically, neither by a system policy nor into a Thunderbird profile. With the feature, the tool install SHALL download the pinned extension XPI to `downloads/` in the checkout, which is gitignored, keep it only when its SHA-256 matches the pinned value, and tell the user how to install it from file. A failed download SHALL only warn.

#### Scenario: Tool install with the feature
- **WHEN** `machine setup` or `machine update` installs the tools on a host with the feature
- **THEN** the verified XPI is in `downloads/` and `git status` of the checkout stays clean

#### Scenario: Wrong checksum
- **WHEN** the downloaded file does not match the pinned SHA-256
- **THEN** it is not saved and a warning is printed

#### Scenario: Second user on the host
- **WHEN** another user of the same host opens Thunderbird
- **THEN** that Thunderbird has no bridge extension unless that user installed it
