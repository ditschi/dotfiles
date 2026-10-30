# Spec Delta

## MODIFIED Requirements

### Requirement: GNOME drop-down terminal extension
On a host with the `gnome` feature, `machine` SHALL install and enable the Ddterm GNOME Shell extension for the user from a `mise`-installed CLI, without root. Guake SHALL NOT be installed or configured; an existing Guake installation SHALL stay untouched.

#### Scenario: GNOME host
- **WHEN** `machine setup` or `machine update` runs on a host with the `gnome` feature in a GNOME session
- **THEN** the Ddterm extension is installed in the user's extension directory and enabled, and running it again changes nothing

#### Scenario: Host without GNOME Shell
- **WHEN** the host has no `gnome` feature or no GNOME Shell (for example a container)
- **THEN** no extension is installed and the run does not fail

#### Scenario: Extension install fails
- **WHEN** the extension cannot be installed (for example no compatible version)
- **THEN** the failure is logged and the rest of the run completes

#### Scenario: Guake was removed by hand
- **WHEN** the user removed the `guake` package and `machine apply` runs on a host with the `gnome` feature
- **THEN** `guake` stays removed

#### Scenario: Guake is still installed
- **WHEN** `guake` is installed on a host with the `gnome` feature and `machine apply` runs
- **THEN** the package stays installed and its settings are not changed

## ADDED Requirements

### Requirement: Nerd Font in the drop-down terminal
On a host with the features `fonts` and `gnome`, `machine` SHALL set the Ddterm terminal font to the Nerd Font (`FiraCode Nerd Font Mono`) and SHALL keep the font size Ddterm had. It SHALL change no other Ddterm setting, and SHALL do nothing when the Ddterm extension is not installed.

#### Scenario: First setup of a GNOME desktop
- **WHEN** `machine setup` runs on a host with `fonts` and `gnome` and installs the Ddterm extension in this run
- **THEN** Ddterm uses `FiraCode Nerd Font Mono` in the size it had before, without a second run

#### Scenario: Size chosen by the user
- **WHEN** the Ddterm font is `Monospace Regular 12` and `machine update` runs
- **THEN** the font becomes `FiraCode Nerd Font Mono 12`, and a further run changes nothing

#### Scenario: Ddterm not installed
- **WHEN** the Ddterm extension is not installed (no `gnome` feature, or the install failed)
- **THEN** no Ddterm setting is written and the run does not fail
