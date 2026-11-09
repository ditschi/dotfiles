# Spec Delta

## ADDED Requirements

### Requirement: Homelab node feature
`homelab-node` SHALL be optional on private servers and excluded on desktops, for work and in containers. It SHALL select no dotfile group.

#### Scenario: Private server menu
- **WHEN** the menu is shown on a private server
- **THEN** `homelab-node` is listed without preselection

#### Scenario: Private desktop menu
- **WHEN** the menu is shown on a private desktop
- **THEN** `homelab-node` is not listed

#### Scenario: Work server
- **WHEN** the menu is shown on a work server
- **THEN** `homelab-node` is not listed
