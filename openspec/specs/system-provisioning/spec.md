# system-provisioning Specification

## Purpose
Defines how Ansible applies packages, tools and system configuration for a host's features.

## Requirements

### Requirement: Ansible applies the feature list
Packages and system configuration SHALL be applied by Ansible through `machine apply`, `machine setup` and `machine update --system`, driven by the host's feature list.

#### Scenario: Host with a feature
- **WHEN** a host has a feature enabled and `machine apply` runs
- **THEN** the packages and configuration of that feature are applied

### Requirement: Package table
Apt packages per feature SHALL be defined in one table (`packages_by_feature` in `group_vars/all/packages.yml`), so that a new apt-only feature needs a single entry next to its row in the feature table (`group_vars/all/features.yml`).

#### Scenario: Adding an apt-only feature
- **WHEN** a feature needs only apt packages
- **THEN** one entry in `packages_by_feature` and one row in the feature table are enough

### Requirement: Local roles
Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `touch_device`, `lid_switch`, `power_profile_switch`, `battery_charge_limit`, `zram_swap` and `cosmic_desktop`; model tuning SHALL be a local role per hardware model, such as `thinkpad_l13_yoga_gen2`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

### Requirement: LLM CLI features
The features `claude-code`, `copilot-cli` and `opencode` SHALL install those CLIs, and only a host with the feature SHALL get the CLI. Private hosts SHALL preselect Claude Code and offer Copilot and opencode without preselecting them; work hosts SHALL preselect Claude Code and Copilot; containers SHALL preselect none, so that container CLIs are opt-in.

#### Scenario: Container profile
- **WHEN** a host has the device `container` and no LLM feature is selected
- **THEN** no LLM CLI is installed

#### Scenario: Private host
- **WHEN** a private host takes the feature defaults
- **THEN** `claude-code` is selected and `copilot-cli` and `opencode` are offered but not selected

### Requirement: OpenSpec installed with an LLM CLI
OpenSpec SHALL be installed whenever at least one LLM CLI feature (`claude-code`, `copilot-cli`, `opencode`) is selected, and SHALL NOT be installed otherwise.

#### Scenario: Work machine
- **WHEN** setup runs on a host with `copilot-cli` selected
- **THEN** OpenSpec is installed

#### Scenario: No LLM CLI
- **WHEN** setup runs in a container without any LLM feature
- **THEN** OpenSpec is not installed

### Requirement: Existing installations are preserved
Provisioning SHALL preserve existing installations where possible: `gh` and `az` with their authentication, an existing Docker provider, an installed `yazi`, and existing LLM CLIs.

#### Scenario: Existing gh login
- **WHEN** `gh` is already installed and authenticated
- **THEN** provisioning does not replace it or remove the login

### Requirement: System roles run with root unless switched off
The workstation playbook SHALL need root through `become` and SHALL only apply system packages and system configuration. Root SHALL be assumed on every host; a host whose host config sets `ansible: false` SHALL skip the playbook, while dotfiles, user-space tools and env management still run.

#### Scenario: Host without root
- **WHEN** a host config sets `ansible: false`
- **THEN** the dotfiles, user-space tools and env management still run and the system roles are not applied

#### Scenario: Root not available without the setting
- **WHEN** a host without `ansible: false` cannot become root
- **THEN** the Ansible run fails with a message that names the setting

### Requirement: Collections and Galaxy roles
`ansible.posix` SHALL be the only required collection, and Galaxy roles SHALL NOT be used; thin local roles are used instead.

#### Scenario: Installing requirements
- **WHEN** the Ansible requirements are installed
- **THEN** only `ansible.posix` is installed

### Requirement: etckeeper outside containers
The feature `etckeeper` SHALL be preselected on every host except those with the device `container`.

#### Scenario: Home laptop
- **WHEN** a private desktop takes its feature defaults
- **THEN** `etckeeper` is included

### Requirement: COSMIC session on Ubuntu from the PPA
On Ubuntu 26.04 or newer, the feature `cosmic` SHALL add the apt source `ppa:hepp3n/cosmic-epoch` with its signing key pinned in the repository, and install `cosmic-session` with its recommended packages. An apt run SHALL accept packages from that source only if they are signed with that key.

#### Scenario: Ubuntu 26.04 desktop
- **WHEN** an Ubuntu 26.04 desktop has the feature `cosmic` and `machine apply` runs
- **THEN** the PPA source is present, `cosmic-session` is installed, and COSMIC can be chosen at login

#### Scenario: Second run
- **WHEN** `machine apply` runs again on that host
- **THEN** the source and the packages are unchanged and nothing is reported as changed

### Requirement: COSMIC keeps GDM as the display manager
When Ansible installs COSMIC on Ubuntu, GDM SHALL stay the default display manager, so that GNOME and COSMIC can both be chosen at login. A host that uses another display manager before the run SHALL keep it.

#### Scenario: GNOME stays available
- **WHEN** COSMIC is installed on an Ubuntu host that logs in through GDM
- **THEN** GDM is still the display manager and offers both GNOME and COSMIC sessions

### Requirement: COSMIC only where it is available
The feature `cosmic` SHALL apply only on desktops, never on servers or in containers. On Pop!_OS it SHALL change nothing, because COSMIC is part of the system. On Ubuntu releases older than 26.04 and on other distributions it SHALL change nothing, and Ansible SHALL print a warning that names the release and the reason.

#### Scenario: Server host config lists cosmic
- **WHEN** a server's host config lists `cosmic` and `machine apply` runs
- **THEN** a warning names `cosmic` as excluded, no apt source is added and no package is installed for it

#### Scenario: Pop!_OS
- **WHEN** a Pop!_OS host has the feature `cosmic` and `machine apply` runs
- **THEN** no apt source is added and no package is installed for `cosmic`

#### Scenario: Ubuntu 24.04
- **WHEN** an Ubuntu 24.04 host has the feature `cosmic` and `machine apply` runs
- **THEN** nothing is installed for `cosmic` and a warning says that the PPA supports only Ubuntu 26.04 and newer

### Requirement: GNOME after COSMIC uses its own settings
On a host with the feature `cosmic`, a GNOME session SHALL start without `DCONF_PROFILE` in the user manager's environment, also when a COSMIC session ran before it without a reboot. The fix SHALL be a dotfile of the group `cosmic` and SHALL need no change to the `machine` CLI.

#### Scenario: GNOME login after COSMIC
- **WHEN** the user logs out of COSMIC and into GNOME without a reboot
- **THEN** `systemctl --user show-environment` has no `DCONF_PROFILE`, and GNOME writes its settings to `~/.config/dconf/user`

### Requirement: Deselecting COSMIC removes nothing
When the feature `cosmic` is removed from a host, Ansible SHALL leave the PPA source and the installed packages in place. The role documentation SHALL describe how to remove them by hand with `ppa-purge`.

#### Scenario: Feature deselected
- **WHEN** `cosmic` is removed from a host's features and `machine apply` runs
- **THEN** the PPA source and the COSMIC packages are still present

### Requirement: Telegraf installed from the InfluxData source
With the feature `monitoring`, Ansible SHALL add the InfluxData apt source with its signing key and install `telegraf` from it on Debian-family hosts. A failed install SHALL fail the run instead of being skipped silently.

#### Scenario: Ubuntu host with monitoring
- **WHEN** `machine apply` runs on an Ubuntu host with `monitoring` and `telegraf` is not installed
- **THEN** the InfluxData source is added and `telegraf` is installed from it

#### Scenario: Install fails
- **WHEN** the InfluxData source cannot be reached and `telegraf` is not installed
- **THEN** the Ansible run fails and names the Telegraf install

### Requirement: Local Telegraf fragments are the default config
Telegraf SHALL use the local fragments resolved from hardware, device and features as its inputs. When `INFLUX_TELEGRAF_CONFIG_BASE` is set, the service SHALL load the remote configs of those names from that base instead of the local fragments, with the Influx token in its environment. The environment file holding the token SHALL be readable by root only.

#### Scenario: No remote base
- **WHEN** `INFLUX_TELEGRAF_CONFIG_BASE` is empty on a laptop with `monitoring`
- **THEN** Telegraf loads the base and laptop fragments from `/etc/telegraf/telegraf.d`

#### Scenario: Remote base set
- **WHEN** `INFLUX_TELEGRAF_CONFIG_BASE` is set
- **THEN** the Telegraf service starts with one `--config` per resolved name under that base instead of the local fragments and has `INFLUX_TOKEN` in its environment, and the file holding it has mode `0600`

### Requirement: Telegraf output from the Influx credentials
When the Influx credentials are available, Ansible SHALL write the Telegraf output: InfluxDB 2.x when a token is set, otherwise InfluxDB 1.x with user and password. A run without credentials SHALL keep an existing output file unchanged.

#### Scenario: Token available
- **WHEN** `machine apply` runs with the Influx URL and token available
- **THEN** an InfluxDB 2.x output with that URL, token, organisation and bucket is written, readable only by root and the group the Telegraf service runs as

#### Scenario: Credentials missing on a later run
- **WHEN** an output was written earlier and `machine apply` runs without Influx credentials
- **THEN** the existing output is kept and Telegraf keeps shipping metrics

### Requirement: Telegraf runs only with an output
Ansible SHALL enable and start Telegraf when an output is configured and SHALL stop and disable it when none is, so that it does not restart in a loop. A failure to start Telegraf with an output SHALL fail the run.

#### Scenario: Output configured
- **WHEN** `machine apply` finishes on a host with `monitoring` and an output
- **THEN** `telegraf` is enabled and active

#### Scenario: No output
- **WHEN** `machine apply` finishes on a host with `monitoring` and no output
- **THEN** `telegraf` is stopped and disabled and the run prints that the Influx credentials are missing

### Requirement: Telegraf health is reported, not reverted
After an apply on a host with `monitoring`, the health check SHALL report whether Telegraf is not installed, has no output or is not active, and SHALL NOT treat any of these as a failure that restores the previous host config.

#### Scenario: Telegraf not active after apply
- **WHEN** `machine apply` succeeds but `telegraf` is not active
- **THEN** a warning names the reason and the applied host config is kept

### Requirement: Telegraf reports the system hostname
Telegraf SHALL report the host's own system hostname, also when Ansible runs locally against the inventory host `localhost`.

#### Scenario: Local apply
- **WHEN** `machine apply` runs locally on the host `homeserver`
- **THEN** Telegraf's metrics carry the host tag `homeserver`, not `localhost`
