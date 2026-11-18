# Spec Delta

## Purpose

Installs the niri compositor with the Dux Modular Shell as an additional login session on desktops with the feature `niri`, and gives it a Ghostty drop-down terminal on F12.

## ADDED Requirements

### Requirement: Feature installs niri, DMS and Ghostty
On an Ubuntu host with the feature `niri` whose release the duxlabs PPAs build, provisioning SHALL add both PPAs signed by a key pinned in the repository and install `niri`, `dms` and `ghostty`. On other hosts it SHALL install nothing and report why, without failing the run.

#### Scenario: Ubuntu 26.04 desktop
- **WHEN** Ansible runs on an Ubuntu 26.04 desktop with the feature `niri`
- **THEN** both PPA sources and the pinned key are present and `niri`, `dms` and `ghostty` are installed

#### Scenario: Release not built
- **WHEN** Ansible runs with the feature `niri` on a release the PPAs do not build
- **THEN** a warning names the release, nothing is installed and the run continues

### Requirement: Display manager stays
Installing the niri session SHALL NOT change the display manager; niri SHALL be selectable as a session at the existing login screen.

#### Scenario: GDM host
- **WHEN** the feature `niri` is applied on a host whose display manager is GDM
- **THEN** GDM is still the display manager and the login screen offers a niri session

### Requirement: One-time DMS setup
After provisioning, `machine setup` and `machine update` SHALL run the DMS setup for niri with Ghostty once on a host with the feature `niri`, DMS installed and no niri config yet. An existing niri or Ghostty config SHALL NOT be replaced.

#### Scenario: Fresh host
- **WHEN** `machine setup` finishes Ansible on a host with the feature `niri` and no `~/.config/niri/config.kdl`
- **THEN** the DMS niri config, its include files, the Ghostty config and the DMS service for the niri session are created

#### Scenario: Existing config
- **WHEN** `machine update` runs on a host that already has `~/.config/niri/config.kdl`
- **THEN** the DMS setup is not run and the file keeps its content apart from the include line

### Requirement: DMS starts only with niri
The DMS service SHALL start with the niri session and SHALL NOT start in other sessions such as GNOME or COSMIC.

#### Scenario: GNOME login
- **WHEN** the user logs in to GNOME on a host with the feature `niri`
- **THEN** `dms.service` is not started

### Requirement: F12 drop-down terminal
In the niri session, F12 SHALL toggle a Ghostty quick terminal that drops down from the top of the screen and hides when it loses focus. The binding and the terminal settings SHALL come from the repository and SHALL be included by the niri and Ghostty configs.

#### Scenario: Toggle
- **WHEN** the user presses F12 twice in a niri session
- **THEN** the drop-down terminal appears at the top and then hides again

#### Scenario: Include kept on update
- **WHEN** `machine update` runs on a host whose niri or Ghostty config lacks the include of the repository file
- **THEN** the include is added once and the rest of the file is unchanged

### Requirement: niri customizations from the dotfiles
The owner's niri customizations SHALL live in one file of the dotfile group `niri` that the niri config includes after the DMS files, linked into the home directory like the other dotfiles, so that every host with the feature gets the same customizations and an edit in the home directory changes the repository.

#### Scenario: New bind on one host
- **WHEN** the owner adds a bind to `~/.config/niri/dotfiles.kdl` on one host and the change reaches another host with `machine update`
- **THEN** the bind works on both hosts without further steps

#### Scenario: Bind overrides DMS
- **WHEN** the customization file binds a key that DMS's binds also use
- **THEN** the binding from the customization file applies

### Requirement: Mod+E opens the file manager
In the niri session, Mod+E SHALL open a file manager window.

#### Scenario: Open file manager
- **WHEN** the user presses Mod+E in a niri session
- **THEN** a file manager window opens

### Requirement: Ghostty over ssh
Ghostty sessions from the dotfile group `niri` SHALL make ssh logins usable on hosts without Ghostty's terminfo: Ghostty SHALL install its terminfo on the remote host, or fall back to a TERM the host knows, while keeping DMS's other shell integration choices.

#### Scenario: Host without Ghostty terminfo
- **WHEN** the user types in zsh with autosuggestions over ssh on a host that had no `xterm-ghostty` terminfo
- **THEN** suggestions and deletions are drawn without leftover characters

### Requirement: Selection goes to the middle-click buffer
In Ghostty sessions from the dotfile group `niri`, selecting text with the mouse SHALL copy it to the primary selection, so that a middle click pastes it.

#### Scenario: Select and middle-click
- **WHEN** the user selects text in Ghostty and middle-clicks in another window
- **THEN** the selected text is pasted
