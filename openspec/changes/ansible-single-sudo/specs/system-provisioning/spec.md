# Spec Delta

## ADDED Requirements

### Requirement: Local Ansible runs need one authentication
For a local Ansible run in a terminal, `machine` SHALL authenticate once through `sudo` in that terminal, with whatever PAM offers (fingerprint or password), and SHALL then run `ansible-playbook` as root. No task of the run SHALL need its own authentication, and `machine` SHALL NOT ask for the sudo password itself.

#### Scenario: Fingerprint before password
- **WHEN** PAM asks for a fingerprint first with a 10 s timeout and the user enters the password after it times out
- **THEN** the playbook runs to the end without a become timeout and without another prompt

#### Scenario: Fingerprint accepted
- **WHEN** the user touches the sensor at the sudo prompt
- **THEN** the playbook runs as root without a password

#### Scenario: Revert run within the sudo ticket
- **WHEN** the apply fails and `machine` runs Ansible again with the restored host config while the sudo ticket of the terminal is still valid
- **THEN** the second run starts without a prompt

### Requirement: Login-user tasks run as the login user
Tasks that act for the login user (the Docker and Compose checks, the GNOME touch-device extensions) SHALL run as the login user who started `machine`, also when `ansible-playbook` runs as root. The touch-device tasks SHALL reach that user's GNOME session.

#### Scenario: Docker check
- **WHEN** the packages play checks the existing Docker CLI during a run as root
- **THEN** `docker --version` runs as the login user with the login user's `PATH`

#### Scenario: Touch device in a GNOME session
- **WHEN** a host with `touch-device` is applied from a terminal inside the user's GNOME session
- **THEN** the extensions are listed and enabled in that user's session, not root's

#### Scenario: authorized_keys owner
- **WHEN** the role `sshd_home` writes `authorized_keys` during a run as root
- **THEN** it writes them for the login user who started `machine`

### Requirement: Ansible without a terminal or as root
Without a terminal, `machine` SHALL run `ansible-playbook` through `sudo` without prompting and SHALL fail with a message when sudo needs authentication. When `machine` already runs as root, it SHALL run `ansible-playbook` directly.

#### Scenario: Update check job without a sudo ticket
- **WHEN** a local Ansible run starts without a terminal and sudo needs a password
- **THEN** no prompt appears, the run fails and the message says that the system changes need an interactive `machine update`

#### Scenario: Container as root
- **WHEN** `machine apply` runs as root
- **THEN** `ansible-playbook` runs without `sudo`

### Requirement: Restricted sudo needs permission for the root run
On a host whose sudo refuses `ansible-playbook` as root, the local Ansible run SHALL fail without falling back to per-task `sudo`, and the message SHALL name the refused command and the host config setting `ansible: false`.

#### Scenario: Sudo limited to selected commands
- **WHEN** sudo on a host allows only selected commands and refuses `ansible-playbook`
- **THEN** the run fails, the message names `ansible-playbook` as the command that needs administrator approval and mentions `ansible: false`

### Requirement: Remote Ansible runs keep per-task become
A remote run (`machine apply --limit <host>` or the `homelab` playbook) SHALL keep running `ansible-playbook` as the login user and SHALL ask for the remote become password as before.

#### Scenario: Remote apply
- **WHEN** `machine apply --limit homeserver` runs in a terminal
- **THEN** `ansible-playbook` runs without `sudo` and asks for the become password of the remote host
