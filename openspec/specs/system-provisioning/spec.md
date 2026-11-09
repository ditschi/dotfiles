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
Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `lid_switch`, `power_profile_switch`, `battery_charge_limit`, `zram_swap`, `memory_headroom` and `cosmic_desktop`; model tuning SHALL be a local role per hardware model, such as `thinkpad_l13_yoga_gen2`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

### Requirement: Local roles need root
Every local Ansible role SHALL do work that needs root. Work for the login user that needs no root, such as installing or enabling GNOME Shell extensions or writing the user's settings, SHALL NOT be done by Ansible; `machine` and `mise` do it (see `user-tools`).

#### Scenario: Adding a GNOME extension for a feature
- **WHEN** a feature needs a GNOME Shell extension for the login user
- **THEN** it is installed by `machine` without root, and no Ansible role or play is added for it

#### Scenario: No touch-device play
- **WHEN** the workstation playbook runs on a host with `touch-device`
- **THEN** no play or role of the playbook installs or enables the touch extensions

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

### Requirement: Telegraf can read SMART data
On a host whose Telegraf configuration includes the SMART fragment, Ansible SHALL install `smartmontools` and SHALL allow the `telegraf` user to run `smartctl`, and only `smartctl`, as root without a password. The rule SHALL be validated before it is put in place, so that an invalid rule never breaks `sudo`. On a host with `monitoring` but without the SMART fragment, Ansible SHALL remove that rule and SHALL NOT install `smartmontools` for Telegraf.

#### Scenario: Physical host with monitoring
- **WHEN** `machine apply` runs on a physical private host with `monitoring`
- **THEN** `smartmontools` is installed, `telegraf` may run `smartctl` through `sudo` without a password, and `telegraf` is active with the SMART input

#### Scenario: Nothing else allowed
- **WHEN** the `telegraf` user runs any command other than `smartctl` through `sudo`
- **THEN** `sudo` refuses it

#### Scenario: Virtual machine
- **WHEN** `machine apply` runs on a virtual machine with `monitoring`
- **THEN** no `smartctl` rule for `telegraf` exists and `smartmontools` is not installed for Telegraf

#### Scenario: Host leaves the SMART fragment
- **WHEN** a host with `monitoring` that had the SMART fragment no longer resolves it (for example after `INFLUX_TELEGRAF_CONFIG_BASE` is set) and `machine apply` runs
- **THEN** the `smartctl` rule for `telegraf` is removed; an installed `smartmontools` package is kept

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

### Requirement: Memory headroom as a local role
The swap file size, the systemd-oomd limit for user sessions and the systemd-oomd swap setting of `-.slice` of the feature `memory-headroom` SHALL be applied by the local role `memory_headroom`, which needs root. The memory limit and the OOM policy of the Claude desktop app SHALL be dotfiles of the group `memory-headroom` and SHALL need no root.

#### Scenario: Host without root
- **WHEN** a host with `memory-headroom` sets `ansible: false`
- **THEN** the Claude app settings are still applied, and the swap file and the oomd settings are not changed

### Requirement: Sudo authentication before the slow steps
When `machine update` or `machine apply` will run local Ansible, `machine` SHALL authenticate sudo and check that sudo allows `ansible-playbook` as root before any step that is slow or asks a question, so that no sudo prompt appears later in the run. It SHALL NOT authenticate when Ansible will not run.

#### Scenario: Update with a system change
- **WHEN** `machine update` in a terminal finds that the host config changed or a relevant system file changed
- **THEN** the sudo prompt comes first, before the environment pull, the dotfile apply and the tool install, and Ansible later starts without a prompt while the ticket is valid

#### Scenario: Home-only update
- **WHEN** `machine update` finds no host-config change and no relevant system file change, and `--system` is not given
- **THEN** no sudo prompt appears

#### Scenario: Apply
- **WHEN** `machine apply` runs local Ansible in a terminal
- **THEN** the sudo prompt comes before the bootstrap tool install

#### Scenario: Ansible is skipped
- **WHEN** the host config has `ansible: false` or `--skip-ansible` is given
- **THEN** no sudo prompt appears

#### Scenario: Automatic update
- **WHEN** the background update runs
- **THEN** it never prompts for sudo and never runs Ansible

### Requirement: Renewed sudo check right before Ansible
Right before it starts local Ansible, `machine` SHALL check the sudo ticket again and SHALL prompt again only when it has expired meanwhile.

#### Scenario: Ticket still valid
- **WHEN** the steps between the early authentication and Ansible took less than the ticket lasts
- **THEN** Ansible starts without a prompt

#### Scenario: Ticket expired
- **WHEN** the steps took longer than the ticket lasts
- **THEN** the sudo prompt appears again right before Ansible and the run continues after authentication

### Requirement: Without sudo, everything that needs no root still runs
When the early sudo authentication fails, or sudo refuses `ansible-playbook` as root, `machine` SHALL report the reason at that point and SHALL NOT start Ansible. `machine update` SHALL still run every step that needs no root and report the Ansible step as failed at the end; `machine apply` SHALL restore the host config as for a failed Ansible run.

#### Scenario: Wrong password in update
- **WHEN** sudo gives up at the start of `machine update` because the password was wrong in every try
- **THEN** the dotfile and tool steps still run, Ansible does not run, and the summary names the failed Ansible step

#### Scenario: Changed host config without sudo
- **WHEN** `machine update` brings a changed host config and sudo gives up at the start
- **THEN** the steps that need no root use the new host config, the host config is restored at the end, and the next update applies it again

#### Scenario: Typo
- **WHEN** the user mistypes the password once and then enters it correctly
- **THEN** sudo asks again, the authentication succeeds and the run continues as usual

#### Scenario: Restricted sudo
- **WHEN** sudo refuses `ansible-playbook` as root
- **THEN** the message of the permission check appears before any slow step

#### Scenario: Without a terminal or with `--no-become`
- **WHEN** sudo would need authentication and there is no terminal or `--no-become` is given
- **THEN** the existing message appears at the start and no prompt is attempted

### Requirement: The failure names its cause
When the sudo authentication fails, the message SHALL say whether the password was wrong or the user has no permission to use sudo, and otherwise SHALL keep a generic text.

#### Scenario: Wrong password
- **WHEN** sudo gives up after incorrect password attempts
- **THEN** the message says the password was wrong and that the command can be run again

#### Scenario: No sudo permission
- **WHEN** sudo reports that the user may not run sudo
- **THEN** the message says the user has no sudo permission and names the administrator as the one to ask
