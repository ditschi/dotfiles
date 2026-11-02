# Spec Delta

## MODIFIED Requirements

### Requirement: Managed SSH config has owner-only permissions
After successfully applying dotfiles, the machine CLI SHALL ensure that the managed `~/.ssh/config` target has mode `0600`. The config SHALL remain a symlink into the checkout with unchanged contents. This guarantee SHALL apply across contexts and devices that select the config's dotfile group. When the checkout is on a read-only file system, the machine CLI SHALL report that the mode could not be set and SHALL NOT fail the apply for that reason.

#### Scenario: Group-writable checkout target
- **WHEN** dotfile apply installs the managed SSH config from a checkout whose config has mode `0664`
- **THEN** the resolved config target has mode `0600`
- **AND** the home-directory config remains a symlink to the checkout with unchanged contents

#### Scenario: Repeated apply repairs permissions
- **WHEN** the managed config is already linked and a later checkout or edit makes its target group-writable
- **THEN** the next successful dotfile apply restores mode `0600`
- **AND** applying again leaves the config linked with mode `0600` and unchanged contents

#### Scenario: Read-only checkout
- **WHEN** dotfile apply runs from a checkout on a read-only file system whose config has mode `0644`
- **THEN** the apply succeeds, the home-directory config is a symlink to the checkout and the output says that mode `0600` could not be set

#### Scenario: Other permission errors
- **WHEN** setting the mode fails for another reason, for example because the user does not own the file
- **THEN** the dotfile apply fails with that error
