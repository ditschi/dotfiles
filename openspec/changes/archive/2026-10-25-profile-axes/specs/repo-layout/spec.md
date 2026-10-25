# Spec Delta

## MODIFIED Requirements

### Requirement: Layered responsibilities
Desired host state SHALL live in `machine/hosts/<hostname>.yml` (context, device and features), the `machine` CLI SHALL orchestrate setup and handle secrets and Git, `mise` SHALL apply the dotfile groups and install the user-space tools, Ansible SHALL install packages and system configuration that need root, and the Ansible inventory SHALL only describe reachability.

#### Scenario: Applying a host
- **WHEN** a host is set up or updated
- **THEN** its context, device and features come from its host config, dotfiles and user-space tools are applied by `mise`, and system packages by Ansible unless the host config switches it off

### Requirement: Groups select what a host receives
Dotfiles SHALL be organised in groups, each a directory of the repository. A host SHALL receive the groups its context, device and features select, files of a group that is no longer selected SHALL be removed from the home directory on the next apply, and only links that point into the repository SHALL be removed. Two selected groups that provide the same target SHALL be reported as a conflict before anything is written.

#### Scenario: Work group on a private host
- **WHEN** a host with the context `private` is applied
- **THEN** no file of the work group is linked

#### Scenario: Profile switch
- **WHEN** a host changes to a context, device or feature list that no longer selects a group and the apply runs
- **THEN** the links of that group are removed and a file that is not a link into the repository is left alone

#### Scenario: Same target in two groups
- **WHEN** two selected groups provide the same target file
- **THEN** the apply reports both groups and writes nothing

#### Scenario: Deleted upstream file
- **WHEN** an update deletes a file from a selected group
- **THEN** its link is removed from the home directory without a separate remove list

#### Scenario: Existing regular file at a target
- **WHEN** a target already exists as a regular file, for example a distribution's default `~/.bashrc`
- **THEN** it is deleted if its content equals the repository file, else moved aside to `<name>.pre-dotfiles` (never overwritten), and the link is created; a link pointing elsewhere into the checkout is replaced
