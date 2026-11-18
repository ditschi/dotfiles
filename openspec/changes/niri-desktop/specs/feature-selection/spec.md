# Spec Delta

## ADDED Requirements

### Requirement: niri desktop feature
The feature `niri` SHALL be offered without preselection on desktops in both contexts, and SHALL be excluded on servers and in containers. It SHALL select the dotfile group `niri`.

#### Scenario: Private desktop menu
- **WHEN** `machine setup` shows the feature menu on a private desktop
- **THEN** `niri` is listed and not preselected

#### Scenario: Work desktop menu
- **WHEN** `machine setup` shows the feature menu on a work desktop
- **THEN** `niri` is listed and not preselected

#### Scenario: Server
- **WHEN** the menu is shown on a server or in a container
- **THEN** `niri` is not listed
