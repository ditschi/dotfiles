# Spec Delta

## MODIFIED Requirements

### Requirement: Work detection in the shell
The shell SHALL set `WORK_SETUP=true` when the context is `work`, or when the user name is a company user ID and the device is not `container`.

#### Scenario: Work host
- **WHEN** a shell starts on a host with the context `work`
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Private host with a company user ID
- **WHEN** a shell starts for a company user ID on a private host that is not a container
- **THEN** `WORK_SETUP` is `true`

#### Scenario: Container with a company user ID
- **WHEN** a shell starts for a company user ID in a container without a context override
- **THEN** `WORK_SETUP` is not set

### Requirement: Work modules only for work
The work modules (`01_work*.zsh`) SHALL belong to a group that only the context `work` selects, and they SHALL return early unless `WORK_SETUP=true`.

#### Scenario: Private profile
- **WHEN** the dotfile groups are applied for a host with the context `private`
- **THEN** no work module is linked

#### Scenario: Work module without work setup
- **WHEN** a linked work module is sourced and `WORK_SETUP` is not `true`
- **THEN** it returns without effect

### Requirement: Work and private stay separate
The separation SHALL also cover the Git default identity (`~/.gitconfig.local`, from the context), the Bitwarden environment group (`work` or `private`, one per context, none in a container without context), the SSH key class (`work` or `home`), and the features of the private infrastructure (`monitoring`, `sshd-home`, `syncthing`, `tailscale`, `thunderbird`), which are excluded for work.

#### Scenario: Private host
- **WHEN** a private host loads secrets
- **THEN** only `env/groups/private` and its host item are queried, never the work group

#### Scenario: Work host
- **WHEN** a work host is set up
- **THEN** none of the private infrastructure features is offered or applied
