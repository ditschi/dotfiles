# Spec Delta

## MODIFIED Requirements

### Requirement: Local roles
Larger system features SHALL be local roles that need root: `monitoring`, `sshd_home`, `stylus_touch_guard`, `touch_device`, `lid_switch`, `power_profile_switch`, `battery_charge_limit`, `zram_swap` and `cosmic_desktop`; model tuning SHALL be a local role per hardware model, such as `thinkpad_l13_yoga_gen2`. User-space tools SHALL NOT be Ansible roles; they are installed by `mise` (see `user-tools`).

#### Scenario: Adding a user-space tool
- **WHEN** a tool is available as a release binary
- **THEN** it is added to a group fragment of `mise` and not to Ansible

## ADDED Requirements

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
