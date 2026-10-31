# Spec Delta

## ADDED Requirements

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
