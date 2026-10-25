# Spec Delta

## ADDED Requirements

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
