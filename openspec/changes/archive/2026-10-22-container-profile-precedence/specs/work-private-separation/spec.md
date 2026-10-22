## MODIFIED Requirements

### Requirement: Work detection in the shell
The shell SHALL set `WORK_SETUP=true` when the profile is `work-machine`, or when the user name is a company user ID and the profile is not `container`.

#### Scenario: Work host
- **WHEN** a shell starts on a `work-machine` host
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Private host with a company user ID
- **WHEN** a shell starts for a company user ID on a host with another profile that is not `container`
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Container with a company user ID
- **WHEN** a shell starts for a company user ID in a container with the `container` profile
- **THEN** `WORK_SETUP` is not set
