# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The machine CLI is not deployed by chezmoi`
- TO: `### Requirement: The machine CLI is not deployed by the dotfile tool`

## MODIFIED Requirements

### Requirement: Home directory files are symlinks into the repository
Dotfiles in the home directory SHALL be symlinks into the repository, created from dotfile groups by `mise`, so that editing a file in the home directory edits the repository checkout. Files in the repository SHALL carry their real names (for example `.zshrc`, not `dot_zshrc`).

#### Scenario: Editing in the home directory
- **WHEN** a user edits a managed file in the home directory
- **THEN** the change appears in the repository checkout and can be committed and synced to other hosts

#### Scenario: Reading the repository
- **WHEN** a user lists a group directory of the repository
- **THEN** the files are named as they are in the home directory

### Requirement: Layered responsibilities
Desired host state SHALL live in `machine/hosts/<hostname>.yml` (profile and features), the `machine` CLI SHALL orchestrate setup and handle secrets and Git, `mise` SHALL apply the dotfile groups and install the user-space tools, Ansible SHALL install packages and system configuration that need root, and the Ansible inventory SHALL only describe reachability.

#### Scenario: Applying a host
- **WHEN** a host is set up or updated
- **THEN** its profile and features come from its host file, dotfiles and user-space tools are applied by `mise`, and system packages by Ansible when root is available

## ADDED Requirements

### Requirement: Groups select what a host receives
Dotfiles SHALL be organised in groups, each a directory of the repository. A host SHALL receive the groups its profile and features select, files of a group that is no longer selected SHALL be removed from the home directory on the next apply, and only links that point into the repository SHALL be removed. Two selected groups that provide the same target SHALL be reported as a conflict before anything is written.

#### Scenario: Work group on a private host
- **WHEN** a host with the profile `home-laptop` is applied
- **THEN** no file of the work group is linked

#### Scenario: Profile switch
- **WHEN** a host changes from a profile that selects a group to one that does not and the apply runs
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

## MODIFIED Requirements

### Requirement: The machine CLI is not deployed by the dotfile tool
The `machine` CLI SHALL live in `machine_cli/` at the repository root, outside the dotfile groups, and `~/.local/bin/machine` SHALL be a symlink into the checkout. The dotfile tool SHALL NOT deploy, copy or prompt about the CLI.

#### Scenario: Plain git pull adds a CLI module
- **WHEN** a user updates the checkout with `git pull` and the incoming commits add a module to the CLI
- **THEN** `machine` runs with the new module without applying the dotfile groups

#### Scenario: Plain git pull changes the entry point
- **WHEN** a user updates the checkout with `git pull` and the incoming commits change the `machine` script
- **THEN** `machine` runs the new script and the dotfile tool does not ask to overwrite it
