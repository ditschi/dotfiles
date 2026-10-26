# feature-selection Specification

## Purpose
Defines how the features of a host are derived from its context and device: one table states per context and device whether a feature is preselected, optional or excluded, and which dotfile groups it selects; the menu, the dotfile groups and Ansible follow it.

## Requirements

### Requirement: One feature table
Every feature SHALL be listed once in a single table in the repository, with its help text, the dotfile groups it selects (none, one or several), and, for each context (`private`, `work`) and each device (`desktop`, `server`, `container`), one of: preselected, optional or excluded. The `machine` CLI and Ansible SHALL both read this table.

#### Scenario: Adding a feature
- **WHEN** a new feature is added
- **THEN** one entry in the table gives its help text, its groups and its values for every context and device

### Requirement: The stricter value wins
For a host, a feature SHALL be excluded when its context or its device excludes it; otherwise optional when either of them makes it optional; otherwise preselected. A container without a context SHALL use only the device value.

#### Scenario: Docker on a work desktop
- **WHEN** the context `work` makes `docker` optional and the device `desktop` preselects it
- **THEN** `docker` is optional and not preselected

#### Scenario: Thunderbird on a private server
- **WHEN** the context `private` preselects `thunderbird` and the device `server` excludes it
- **THEN** `thunderbird` is excluded

### Requirement: Dotfile groups from the table
A host SHALL receive `core` and `prompt` always, `systemd` unless the device is `container`, `work` when the context is `work`, and the groups that the table names for each of its features. Adding a feature with its own group SHALL need no change to the `machine` CLI.

#### Scenario: Thunderbird selected
- **WHEN** a private desktop has the feature `thunderbird`
- **THEN** the group `thunderbird` is applied

#### Scenario: Two features share a group
- **WHEN** a host has `claude-code` and `copilot-cli`, which both name the group `openspec`
- **THEN** `openspec` is applied once

### Requirement: Features for every host
`zsh-full` SHALL be preselected everywhere. `etckeeper` and `ssh-host-key` SHALL be preselected for every context and for desktops and servers, and excluded in containers.

#### Scenario: Container
- **WHEN** a container takes the defaults
- **THEN** only `zsh-full` is preselected

### Requirement: LLM features
`claude-code`, `copilot-cli` and `opencode` SHALL be optional in containers. `claude-code` SHALL be preselected for private and for work; `copilot-cli` SHALL be preselected for work and optional for private. `opencode` SHALL be optional for private and for work.

#### Scenario: New private desktop
- **WHEN** a new private desktop takes the defaults
- **THEN** `claude-code` is preselected and `copilot-cli` is offered but not preselected

#### Scenario: Container menu
- **WHEN** the menu is shown in a container
- **THEN** `claude-code`, `copilot-cli` and `opencode` are listed without preselection

### Requirement: Features for graphical sessions
`fonts`, `desktop` and `gnome` SHALL be preselected on desktops; `cosmic`, `stylus-touch-guard` and `touch-device` SHALL be optional on desktops. All six SHALL be excluded on servers and in containers, for every context.

#### Scenario: Server menu
- **WHEN** the menu is shown on a server
- **THEN** none of `fonts`, `desktop`, `gnome`, `cosmic`, `stylus-touch-guard`, `touch-device` is listed

### Requirement: Features by context
`kerberos` and `azure-cli` SHALL be preselected for work and excluded for private. `docker` SHALL be preselected for private and optional for work. `unattended-upgrades` SHALL be preselected for private and excluded for work. All four SHALL be excluded in containers.

#### Scenario: New work desktop
- **WHEN** a new host with context `work` and device `desktop` takes the defaults
- **THEN** `copilot-cli`, `kerberos` and `azure-cli` are preselected, `docker` is offered but not preselected, and `unattended-upgrades` is not offered

### Requirement: Features of the private infrastructure
`monitoring` and `sshd-home` SHALL be preselected for private desktops and servers. `syncthing` and `thunderbird` SHALL be preselected for private desktops and excluded on servers. `tailscale` SHALL be optional for private desktops and servers. All five SHALL be excluded for work and in containers.

#### Scenario: New private desktop with infrastructure
- **WHEN** a new host with context `private` and device `desktop` takes the defaults
- **THEN** `monitoring`, `sshd-home`, `syncthing`, `thunderbird` and `docker` are preselected, `tailscale` is offered but not preselected, and `kerberos` is not offered

#### Scenario: Private server
- **WHEN** the menu is shown on a private server
- **THEN** `syncthing` and `thunderbird` are not listed and `tailscale` is listed without preselection

### Requirement: Menu shows only allowed features
The feature menu of `machine setup` SHALL list only the features that are not excluded for the host, with the preselected ones marked. Features the host already has SHALL stay selected.

#### Scenario: Private host menu
- **WHEN** `machine setup` shows the feature menu on a private host
- **THEN** `kerberos` and `azure-cli` are not listed

### Requirement: Excluded features in a host config
When a host config lists a feature that is excluded for its context or device, or a feature that no longer exists, `machine` SHALL report it on `setup`, `apply` and `update`, Ansible SHALL NOT apply it, and the next time `machine` writes the host config the feature SHALL be left out.

#### Scenario: Monitoring on a work host
- **WHEN** a work host config lists `monitoring` and `machine apply` runs
- **THEN** a warning names `monitoring`, Telegraf is not configured, and the next `machine setup` writes the file without it

#### Scenario: Removed feature
- **WHEN** a host config still lists `starship`, which is no longer a feature
- **THEN** a warning names it and the next write drops it

### Requirement: Laptop and swap features
`lid-switch`, `power-profile-switch` and `battery-charge-limit` SHALL be preselected on desktops for both contexts and excluded on servers and in containers. `zram-swap` SHALL be preselected on desktops and servers for both contexts and excluded in containers. There SHALL be no feature for the tuning of one hardware model.

#### Scenario: New private desktop
- **WHEN** a new private desktop takes the defaults
- **THEN** `lid-switch`, `power-profile-switch`, `battery-charge-limit` and `zram-swap` are preselected

#### Scenario: New private server
- **WHEN** a new private server takes the defaults
- **THEN** `zram-swap` is preselected and none of the three laptop features is offered

#### Scenario: Container menu
- **WHEN** the menu is shown in a container
- **THEN** none of the four features is listed

### Requirement: Interactive selection by checklist
In a terminal, the selection of features SHALL be a checklist: the arrow keys move, space toggles the entry under the cursor, Enter confirms, and the preselected features are ticked. Where the terminal cannot deliver key presses, the selection SHALL fall back to a prompt where numbers toggle entries relative to the preselection.

#### Scenario: Selecting with the keyboard
- **WHEN** a user runs `machine setup` in a terminal and presses down, space and Enter on a preselected feature list
- **THEN** the second feature's tick is flipped and the others keep their preselection

#### Scenario: Keys cannot be read
- **WHEN** key presses cannot be read from the terminal
- **THEN** the user toggles features by number, Enter keeping the preselection
