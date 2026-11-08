# Spec Delta

## ADDED Requirements

### Requirement: GNOME touch extensions without root
On a host with the feature `touch-device`, `machine` SHALL install the GNOME Shell extensions TouchUp and Screen Rotate in the user's extension directory and enable them, without root and without Ansible, from a `mise`-installed CLI. The feature `touch-device` SHALL make that CLI available also on a host without the feature `gnome`.

#### Scenario: Touch host in a GNOME session
- **WHEN** `machine setup`, `machine apply` or `machine update` runs on a host with `touch-device` and GNOME Shell
- **THEN** TouchUp and Screen Rotate are installed for the user and enabled, and running it again changes nothing

#### Scenario: Touch host without the gnome feature
- **WHEN** a host has `touch-device` but not `gnome`
- **THEN** the extension CLI is installed and the touch extensions are installed and enabled, while the extensions of the feature `gnome` are not and the dotfile group `gnome` is not selected

#### Scenario: Extensions installed by the former Ansible role
- **WHEN** the touch extensions are already in the user's extension directory
- **THEN** they are not installed again, only enabled

#### Scenario: Host without the feature or without GNOME Shell
- **WHEN** the host has no `touch-device` or no GNOME Shell
- **THEN** no touch extension is installed and the run does not fail

#### Scenario: Touch extension install fails
- **WHEN** a touch extension cannot be installed (for example no version for the installed GNOME Shell)
- **THEN** the failure is logged with its reason, the rest of the run completes, and the settings of the `gnome` extensions are still loaded once
