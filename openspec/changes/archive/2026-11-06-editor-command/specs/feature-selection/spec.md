# Spec Delta

## ADDED Requirements

### Requirement: Editor command feature
`editor-command` SHALL be preselected on private and work desktops, optional on servers, and excluded in containers. It SHALL select the dotfile group `editor-command`.

#### Scenario: New desktop
- **WHEN** a new private or work desktop takes the defaults
- **THEN** `editor-command` is preselected and the group `editor-command` is applied

#### Scenario: Server menu
- **WHEN** the menu is shown on a server
- **THEN** `editor-command` is offered but not preselected

#### Scenario: Container menu
- **WHEN** the menu is shown in a container
- **THEN** `editor-command` is not listed
