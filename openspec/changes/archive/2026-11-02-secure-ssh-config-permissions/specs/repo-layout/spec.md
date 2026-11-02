# Spec Delta

## ADDED Requirements

### Requirement: Managed SSH config has owner-only permissions
After successfully applying dotfiles, the machine CLI SHALL ensure that the managed `~/.ssh/config` target has mode `0600`. The config SHALL remain a symlink into the checkout with unchanged contents. This guarantee SHALL apply across contexts and devices that select the config's dotfile group.

#### Scenario: Group-writable checkout target
- **WHEN** dotfile apply installs the managed SSH config from a checkout whose config has mode `0664`
- **THEN** the resolved config target has mode `0600`
- **AND** the home-directory config remains a symlink to the checkout with unchanged contents

#### Scenario: Repeated apply repairs permissions
- **WHEN** the managed config is already linked and a later checkout or edit makes its target group-writable
- **THEN** the next successful dotfile apply restores mode `0600`
- **AND** applying again leaves the config linked with mode `0600` and unchanged contents
