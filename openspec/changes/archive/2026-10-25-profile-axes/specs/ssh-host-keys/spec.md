# Spec Delta

## MODIFIED Requirements

### Requirement: Whole key backed up as a Bitwarden SSH key item
The host's key SHALL be stored as a Bitwarden item of type SSH key named `ssh/<class>/hosts/<hostname>`, with private key, public key and fingerprint. There SHALL be no option to store only the public key. The class SHALL be `home` for the context `private` and `work` for the context `work`. Only items of type SSH key SHALL be read; secure notes with the same name SHALL be ignored.

#### Scenario: Key uploaded
- **WHEN** setup uploads the key of a home host
- **THEN** the item `ssh/home/hosts/<hostname>` of type SSH key holds the private key, the public key and the fingerprint

#### Scenario: Old secure note present
- **WHEN** a secure note with the item's name exists and no SSH key item
- **THEN** the note is neither read nor changed, and the key is stored in a new SSH key item
