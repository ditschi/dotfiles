# Spec Delta

## ADDED Requirements

### Requirement: Homelab age key in Bitwarden
`machine setup`, `machine apply` and the apply step of `machine update` SHALL read the Bitwarden item `homelab-age-<host>` before Ansible runs when the host has `homelab-node`, and use its hidden field `private_key`. Hosts without the feature SHALL NOT read it.

#### Scenario: oracle apply
- **WHEN** `machine apply` runs on a host with `homelab-node`, `homelab.host: oracle` and Bitwarden unlocked
- **THEN** `homelab-age-oracle` is read before Ansible and the key file is written in the same run

#### Scenario: Host without the feature
- **WHEN** the host does not have `homelab-node`
- **THEN** no `homelab-age-*` item is read

### Requirement: Homelab age key stays out of the shell environment
The age key SHALL reach only the Ansible run, through a file readable only by the user and removed when the command ends. It SHALL NOT be written to `~/.env`, `~/.env.host` or `~/.env.local`, logged or printed.

#### Scenario: After apply
- **WHEN** `machine apply` has read `homelab-age-contabo`
- **THEN** no env file and no log contains the key and the temporary file is gone

### Requirement: Missing homelab age item does not block the run
When Bitwarden is locked, not installed, or has no item `homelab-age-<host>` or no field `private_key` in it, the run SHALL continue, keep an existing key file and log which item is missing. `machine attention` SHALL report it while the deploy user has no key file. A run without a terminal SHALL NOT prompt for it.

#### Scenario: Item missing on a new host
- **WHEN** `machine apply` runs on a new host with `homelab-node` and the item does not exist
- **THEN** the run finishes, and `machine attention` names `homelab-age-<host>`
