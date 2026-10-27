# Spec Delta

## ADDED Requirements

### Requirement: GNOME drop-down terminal extension
On a host with the `gnome` feature, `machine` SHALL install and enable the Ddterm GNOME Shell extension for the user from a `mise`-installed CLI, without root. Guake SHALL stay installed.

#### Scenario: GNOME host
- **WHEN** `machine setup` or `machine update` runs on a host with the `gnome` feature in a GNOME session
- **THEN** the Ddterm extension is installed in the user's extension directory and enabled, and running it again changes nothing

#### Scenario: Host without GNOME Shell
- **WHEN** the host has no `gnome` feature or no GNOME Shell (for example a container)
- **THEN** no extension is installed and the run does not fail

#### Scenario: Extension install fails
- **WHEN** the extension cannot be installed (for example no compatible version)
- **THEN** the failure is logged and the rest of the run completes

### Requirement: GNOME extension set
On a host with the `gnome` feature, `machine` SHALL also install and enable gTile, Clipboard Indicator, Quick Settings Audio Panel, Quick Settings Audio Devices Hider and Astra Monitor, and SHALL enable Tiling Assistant from the system installation without installing it again.

#### Scenario: Extensions missing
- **WHEN** `machine update` runs and an extension of the set is not installed
- **THEN** it is installed and enabled, and installed ones are left as they are

#### Scenario: Tiling Assistant
- **WHEN** the system provides Tiling Assistant
- **THEN** it is enabled and no copy is installed in the user's extension directory

### Requirement: Shared GNOME extension settings
The repository SHALL carry the shared settings of these extensions, including a Clipboard Indicator history of 150 entries, and `machine` SHALL load them once per host after the extensions are installed. It SHALL NOT overwrite values the user changed afterwards.

#### Scenario: First load
- **WHEN** `machine update` runs on a `gnome` host that has not loaded the settings
- **THEN** the shared settings are applied and the load is recorded

#### Scenario: Later update
- **WHEN** the settings were loaded before and the user changed a value
- **THEN** `machine update` keeps the user's value

### Requirement: Host-specific extension settings stay local
The repository SHALL NOT ship settings that name local hardware (audio device names of the Audio Devices Hider, Astra Monitor's storage device) or that the extension writes as runtime state.

#### Scenario: Shipped settings checked
- **WHEN** the repository checks run
- **THEN** they fail if a shipped settings file contains such a key
