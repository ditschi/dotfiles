## Purpose

Defines the Bitwarden CLI, session handling and the Ansible Vault password.

## ADDED Requirements

### Requirement: Bitwarden CLI installed for the user
The Bitwarden CLI `bw` SHALL be installed to `~/.local/bin`.

#### Scenario: Setup
- **WHEN** the Bitwarden tooling is set up
- **THEN** `bw` is available in `~/.local/bin`

### Requirement: Session storage is opt-in
Storing `BW_SESSION` SHALL be opt-in with a default of no, and SHALL never be done non-interactively.

#### Scenario: Non-interactive run
- **WHEN** `machine env pull` runs without a terminal
- **THEN** `BW_SESSION` is not written to any file

### Requirement: Ansible Vault password in Bitwarden
The Ansible Vault password SHALL be kept in the Bitwarden item `ansible-vault`, and the real inventory SHALL be vault-encrypted.

#### Scenario: Reading the inventory
- **WHEN** Ansible reads the real inventory
- **THEN** it is decrypted with the password from the `ansible-vault` item
