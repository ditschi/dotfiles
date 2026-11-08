# Spec Delta

## ADDED Requirements

### Requirement: Local roles need root
Every local Ansible role SHALL do work that needs root. Work for the login user that needs no root, such as installing or enabling GNOME Shell extensions or writing the user's settings, SHALL NOT be done by Ansible; `machine` and `mise` do it (see `user-tools`).

#### Scenario: Adding a GNOME extension for a feature
- **WHEN** a feature needs a GNOME Shell extension for the login user
- **THEN** it is installed by `machine` without root, and no Ansible role or play is added for it

#### Scenario: No touch-device play
- **WHEN** the workstation playbook runs on a host with `touch-device`
- **THEN** no play or role of the playbook installs or enables the touch extensions

## MODIFIED Requirements

### Requirement: Local roles
Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `lid_switch`, `power_profile_switch`, `battery_charge_limit`, `zram_swap` and `cosmic_desktop`; model tuning SHALL be a local role per hardware model, such as `thinkpad_l13_yoga_gen2`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

### Requirement: Login-user tasks run as the login user
Tasks that act for the login user (the Docker and Compose checks) SHALL run as the login user who started `machine`, also when `ansible-playbook` runs as root.

#### Scenario: Docker check
- **WHEN** the packages play checks the existing Docker CLI during a run as root
- **THEN** `docker --version` runs as the login user with the login user's `PATH`

#### Scenario: Touch device in a GNOME session
- **WHEN** a host with `touch-device` is applied from a terminal inside the user's GNOME session
- **THEN** Ansible does not touch the extensions; `machine` enables them as that user in that user's session, not root's

#### Scenario: authorized_keys owner
- **WHEN** the role `sshd_home` writes `authorized_keys` during a run as root
- **THEN** it writes them for the login user who started `machine`
