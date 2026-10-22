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

### Requirement: Single entry point
`./bootstrap` SHALL be the single entry point for a new host, and the repository SHALL NOT ship an `install.py` wrapper. The extended mode of the project container launcher SHALL run `./bootstrap` inside the container.

#### Scenario: New host
- **WHEN** a user runs `./bootstrap` on a new host
- **THEN** `uv` is installed if missing and `machine setup` runs

#### Scenario: Extended project container
- **WHEN** `sdx` starts a project container
- **THEN** the launcher runs `./bootstrap --profile container --yes --no-become` from the mounted dotfiles checkout

### Requirement: The machine CLI is not deployed by chezmoi
The `machine` CLI SHALL live in `machine_cli/` at the repository root, outside the chezmoi source tree, and `~/.local/bin/machine` SHALL be a symlink into the checkout. Chezmoi SHALL NOT deploy, copy or prompt about the CLI.

#### Scenario: Plain git pull adds a CLI module
- **WHEN** a user updates the checkout with `git pull` and the incoming commits add a module to the CLI
- **THEN** `machine` runs with the new module without running chezmoi

#### Scenario: Plain git pull changes the entry point
- **WHEN** a user updates the checkout with `git pull` and the incoming commits change the `machine` script
- **THEN** `machine` runs the new script and chezmoi does not ask to overwrite it

### Requirement: The checkout location is not fixed
The `machine` CLI SHALL find the repository by resolving the symlink `~/.local/bin/machine`, so the checkout MAY be at any path.

#### Scenario: Checkout outside the default location
- **WHEN** the repository is cloned to a path other than `~/dotfiles` and bootstrap has linked `machine`
- **THEN** `machine` operates on that checkout
