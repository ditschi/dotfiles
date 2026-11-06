# Spec Delta

## ADDED Requirements

### Requirement: Memory headroom feature
`memory-headroom` SHALL be preselected on private desktops, optional on work desktops, and excluded on servers and in containers. It SHALL select the dotfile group `memory-headroom`.

#### Scenario: New private desktop
- **WHEN** a new private desktop takes the defaults
- **THEN** `memory-headroom` is preselected and the group `memory-headroom` is applied

#### Scenario: Work desktop
- **WHEN** the menu is shown on a work desktop
- **THEN** `memory-headroom` is offered but not preselected

#### Scenario: Server or container menu
- **WHEN** the menu is shown on a server or in a container
- **THEN** `memory-headroom` is not listed
