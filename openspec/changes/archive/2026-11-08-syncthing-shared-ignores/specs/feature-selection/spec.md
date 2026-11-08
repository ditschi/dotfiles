# Spec Delta

## MODIFIED Requirements

### Requirement: Features of the private infrastructure
`monitoring` and `sshd-home` SHALL be preselected for private desktops and servers. `syncthing` SHALL be preselected for private desktops and optional on servers. `thunderbird` SHALL be preselected for private desktops and excluded on servers. `tailscale` SHALL be optional for private desktops and servers. All five SHALL be excluded for work and in containers.

#### Scenario: New private desktop with infrastructure
- **WHEN** a new host with context `private` and device `desktop` takes the defaults
- **THEN** `monitoring`, `sshd-home`, `syncthing`, `thunderbird` and `docker` are preselected, `tailscale` is offered but not preselected, and `kerberos` is not offered

#### Scenario: Private server
- **WHEN** the menu is shown on a private server
- **THEN** `thunderbird` is not listed, and `syncthing` and `tailscale` are listed without preselection
