# bootstrap Specification

## Purpose
Defines how a new host reaches a working setup from a checkout with no prerequisites except a shell and network access.

## Requirements

### Requirement: Self-contained bootstrap
The bootstrap script SHALL install `uv` when it is missing and then run `machine setup`, so that no other tooling has to be prepared by hand.

#### Scenario: uv missing
- **WHEN** bootstrap runs and `uv` is not installed
- **THEN** `uv` is installed for the user and `machine setup` runs

#### Scenario: uv present
- **WHEN** bootstrap runs and `uv` is installed
- **THEN** `machine setup` runs without reinstalling `uv`

### Requirement: machine runs through uv
The `machine` command SHALL be a script run by `uv` with its dependencies declared in the script, for Python 3.11 to 3.13.

#### Scenario: Running machine
- **WHEN** a user runs `machine`
- **THEN** `uv` provides an environment with the declared dependencies and the command starts

### Requirement: Bootstrap runs from a checkout or piped
`./bootstrap` SHALL detect whether it runs from a checkout of the repository or piped from the network (`curl | bash`). When piped, it SHALL clone the repository over HTTPS to `~/dotfiles`, or to the path in `DOTFILES_DIR` when set, and continue from that clone. The repository is assumed to be public; piped bootstrap does not work for a non-public repository.

#### Scenario: Run from a checkout
- **WHEN** a user runs `./bootstrap` inside a checkout
- **THEN** that checkout is used and nothing is cloned

#### Scenario: Piped run on a new host
- **WHEN** bootstrap is piped from the network and no clone exists at the target path
- **THEN** the repository is cloned to `~/dotfiles` (or `DOTFILES_DIR`) and setup continues from the clone

### Requirement: Bootstrap does not update an existing clone
When the clone target already exists, bootstrap SHALL use it without pulling and run `machine setup`. Updating the checkout SHALL stay the job of `machine update`.

#### Scenario: Piped run with an existing clone
- **WHEN** bootstrap is piped and the target path already holds a clone
- **THEN** the clone is left as it is and `machine setup` runs from it

### Requirement: Bootstrap links the machine command
Bootstrap SHALL create or replace `~/.local/bin/machine` as a symlink to the CLI script in the checkout it uses, replacing a regular file left by an earlier layout.

#### Scenario: Host with the earlier copied entry point
- **WHEN** bootstrap runs on a host where `~/.local/bin/machine` is a regular file
- **THEN** it is replaced by a symlink into the checkout and `machine` runs from the checkout

### Requirement: Bootstrap installs mise
The bootstrap script SHALL install `mise` for the user when it is missing, without root, before `machine setup` applies the dotfile groups and the user-space tools, and SHALL leave an installed `mise` as it is.

#### Scenario: mise missing
- **WHEN** bootstrap runs and `mise` is not installed
- **THEN** `mise` is installed to the user's home and `machine setup` runs

#### Scenario: mise present
- **WHEN** bootstrap runs and `mise` is installed
- **THEN** it is not reinstalled

### Requirement: Setup applies the shell environment before Ansible
`machine setup` SHALL pull the env files, then apply the dotfile groups and install the user-space tools, and only then run Ansible, in the same order as `machine update`. When Ansible follows and the dotfile groups and tools were applied, setup SHALL say that the shell is ready in a new terminal while Ansible continues. The SSH host key, the Tailscale login and the update timers SHALL follow Ansible.

#### Scenario: Fresh setup with Ansible
- **WHEN** a user runs `machine setup` on a host where Ansible runs
- **THEN** the env files are pulled, then the dotfile groups and the user-space tools are applied, a line says the shell is ready in a new terminal, and Ansible runs afterwards

#### Scenario: Env questions before the tool install
- **WHEN** the env pull asks about a local-only key during `machine setup` on a terminal
- **THEN** the question comes before the user-space tools are installed

#### Scenario: Steps after Ansible
- **WHEN** setup has run Ansible
- **THEN** it provisions the SSH host key, offers the Tailscale login and enables the update timers after Ansible

#### Scenario: Dotfiles skipped
- **WHEN** a user runs `machine setup --skip-dotfiles`
- **THEN** no env files, dotfile groups or tools are applied, no ready line is printed, and Ansible runs as before

#### Scenario: Ansible skipped
- **WHEN** Ansible is skipped by `--skip-ansible` or `ansible: false`
- **THEN** the env files, the dotfile groups and the user-space tools are applied, no ready line is printed, and setup reports that Ansible was skipped

### Requirement: Setup tries every independent step
`machine setup` SHALL run each step after the host config is written even when an earlier one failed, unless the step needs the failed one. The env pull, the dotfile apply, the tool install, Ansible, the SSH host key and the update timers are steps; the tool install needs the dotfile apply. At the end setup SHALL list each failed or skipped step with its reason and exit with a non-zero status. An interruption by the user SHALL stop setup at once.

#### Scenario: Env pull fails
- **WHEN** the env pull fails during `machine setup`, for example because `bw sync` cannot reach the server
- **THEN** the dotfile groups and the tools are applied, the ready line is printed, Ansible runs, and setup ends with an error that names the env pull

#### Scenario: Dotfile apply fails
- **WHEN** the dotfile apply fails during `machine setup`
- **THEN** the tool install is reported as skipped because of it, no ready line is printed, Ansible and the later steps still run, and setup ends with an error

#### Scenario: Ansible fails
- **WHEN** Ansible fails during `machine setup`
- **THEN** the env files, the dotfile groups and the user-space tools stay applied, the SSH host key and the update timers are still handled, and setup ends with an error that names Ansible

#### Scenario: Interrupted
- **WHEN** the user interrupts `machine setup` with Ctrl-C during a step
- **THEN** no further step runs
