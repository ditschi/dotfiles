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

### Requirement: Bridge extension through a system policy
With the feature, Ansible SHALL add the signed extension `thunderbird-ai@extension` from a pinned release URL to `ExtensionSettings` in `/etc/thunderbird/policies/policies.json`, so that Thunderbird installs it on its next start without manual steps. Other content of that file SHALL be kept.

#### Scenario: Fresh host
- **WHEN** `machine apply` runs on a host with the feature and no policy file
- **THEN** the policy file exists with the extension entry, and the next Thunderbird start installs the extension

#### Scenario: Existing policies
- **WHEN** the policy file already contains other policies
- **THEN** they are still present after the apply

### Requirement: CLI and bridge only with the extension
`thunderbird-cli` and `thunderbird-cli-bridge` SHALL be user tools of a dotfile group `thunderbird` that only the `thunderbird` feature selects. They SHALL NOT be installed on a host without that feature.

#### Scenario: Host with the feature
- **WHEN** `machine setup` runs with the feature
- **THEN** `tb` and `tb-bridge` are on `PATH`

#### Scenario: Host without the feature
- **WHEN** the feature is not selected
- **THEN** neither tool is installed
