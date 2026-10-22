# repo-layout Specification

## Purpose
Defines how dotfiles are stored and applied and how responsibilities are split between host state, the machine CLI, chezmoi and Ansible, so that one repository serves work and private machines.

## Requirements

### Requirement: Home directory files are symlinks into the repository
Dotfiles in the home directory SHALL be symlinks into the repository (chezmoi in symlink mode), so that editing a file in the home directory edits the repository checkout.

#### Scenario: Editing in the home directory
- **WHEN** a user edits a managed file in the home directory
- **THEN** the change appears in the repository checkout and can be committed and synced to other hosts

### Requirement: Layered responsibilities
Desired host state SHALL live in `machine/hosts/<hostname>.yml` (profile and features), the `machine` CLI SHALL orchestrate setup and handle secrets and Git, chezmoi SHALL apply the dotfiles, Ansible SHALL install packages and system configuration, and the Ansible inventory SHALL only describe reachability.

#### Scenario: Applying a host
- **WHEN** a host is set up or updated
- **THEN** its profile and features come from its host file, dotfiles are applied by chezmoi and packages by Ansible

### Requirement: Guided setup and safe update
The `machine` CLI SHALL guide new hosts through setup and SHALL provide a clear and safe update path for existing hosts.

#### Scenario: New host
- **WHEN** a user runs setup on a host without a host file
- **THEN** the CLI guides the user through the choices needed

#### Scenario: Existing host
- **WHEN** a user runs update on a set up host
- **THEN** the host is updated from the repository
