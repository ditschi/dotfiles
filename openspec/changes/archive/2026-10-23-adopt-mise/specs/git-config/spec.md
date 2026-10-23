# Spec Delta

## MODIFIED Requirements

### Requirement: Host-local Git config
`~/.gitconfig.local` SHALL be host-local and not versioned. `machine setup` SHALL create it once from the profile (default identity from the profile, and `safe.directory` on work and container profiles) when it does not exist, and nothing SHALL overwrite it afterwards. Git SHALL treat a missing file as empty, so a host without the file works.

#### Scenario: Update on an existing host
- **WHEN** `machine setup` or `machine update` runs and `~/.gitconfig.local` exists
- **THEN** the file is left unchanged

#### Scenario: Existing work host without the CA bundle key
- **WHEN** the dotfile apply runs on a work host whose `~/.gitconfig.local` has no `http.sslCAInfo`
- **THEN** only that key is appended (the user-space Git ignores the system CA store) and nothing else in the file changes

#### Scenario: First setup
- **WHEN** `machine setup` runs on a host without `~/.gitconfig.local`
- **THEN** the file is created with the identity of the profile

#### Scenario: File missing later
- **WHEN** the file is deleted and Git runs before the next setup
- **THEN** Git reports no error
