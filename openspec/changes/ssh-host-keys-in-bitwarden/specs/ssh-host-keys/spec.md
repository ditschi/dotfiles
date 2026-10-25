# Spec Delta

## ADDED Requirements

### Requirement: Whole key backed up as a Bitwarden SSH key item
`machine ssh publish` SHALL store the host's key as a Bitwarden item of type SSH key named `ssh/<class>/hosts/<hostname>`, with private key, public key and fingerprint. It SHALL have no option to publish only the public key. The class SHALL be `home` or `work` from the profile.

#### Scenario: Publish
- **WHEN** a user runs `machine ssh publish` on a home host
- **THEN** the item `ssh/home/hosts/<hostname>` of type SSH key holds the private key, the public key and the fingerprint

#### Scenario: Item exists with another key
- **WHEN** the item exists with a different key and the command runs on a terminal
- **THEN** both fingerprints are shown and the user is asked whether to update the item (default no)

#### Scenario: Other key without a terminal
- **WHEN** the item exists with a different key and no terminal is available
- **THEN** the item is left unchanged and the difference is reported

### Requirement: Every host gets a key
With the feature `ssh-host-key`, `machine setup` SHALL, in this order: restore the key from the host's Bitwarden item when one exists and no local key is selected; otherwise upload the selected existing local key; otherwise generate an ed25519 key without passphrase on the host and upload it.

#### Scenario: Reinstalled host
- **WHEN** setup runs on a fresh install of a host that has an item in Bitwarden
- **THEN** its key is restored and the host keeps its identity

#### Scenario: New host without a key
- **WHEN** setup runs on a host without a local key and without an item
- **THEN** an ed25519 key is generated on the host and uploaded

#### Scenario: Bitwarden not unlocked
- **WHEN** setup runs unattended or Bitwarden cannot be unlocked
- **THEN** no key is generated or uploaded and setup says how to finish (`machine ssh publish`)

### Requirement: Key check during update
`machine update` SHALL compare the host's key with its Bitwarden item only when a valid Bitwarden session is available without a prompt (environment or `~/.env.local`). A missing item or a different key SHALL become an attention item that `machine` offers to resolve (upload or update the item). Without such a session the check SHALL be skipped silently: no prompt and no message. The update SHALL never generate, restore or upload a key by itself.

#### Scenario: Key not backed up
- **WHEN** `machine update` runs with a saved valid session and the host's key has no item
- **THEN** an attention item says the key is not in Bitwarden, and `machine` offers to upload it

#### Scenario: No session
- **WHEN** `machine update` runs and no valid session is available without a prompt
- **THEN** no key check runs and nothing is printed about it

### Requirement: Existing keys are kept
Existing local keys SHALL keep their path, permissions and passphrase, and SHALL be selected in the current order: `MACHINE_SSH_KEY`, `id_ed25519`, `id_rsa`, a hostname key, a sole other candidate. Restore SHALL never overwrite an existing private key.

#### Scenario: Host with an existing key
- **WHEN** the host has a key and no item exists
- **THEN** that key is uploaded unchanged

#### Scenario: Restore with a local key present
- **WHEN** restore would write a private key where one already exists
- **THEN** restore stops and leaves the existing key unchanged

### Requirement: Public keys of home hosts in the repository
For the `home` class, setup and publish SHALL write the public key to `machine/ssh_keys/<hostname>.pub` and offer to commit it. Keys of the `work` class SHALL NOT be written to the repository. `authorized_keys` SHALL be filled only by the Ansible role `sshd_home` from `machine/ssh_keys/` for the hosts in `ssh_allow_from`; `machine` SHALL NOT read public keys from Bitwarden for `authorized_keys`.

#### Scenario: Apply with ssh_allow_from
- **WHEN** `machine apply` runs on a host with `ssh_allow_from: [homeserver]` and `machine/ssh_keys/homeserver.pub` exists
- **THEN** that key is in `authorized_keys` and no Bitwarden lookup happens

#### Scenario: Choosing ssh_allow_from
- **WHEN** setup offers hosts for `ssh_allow_from`
- **THEN** it offers the hosts with a file in `machine/ssh_keys/`

#### Scenario: Work host
- **WHEN** a work host publishes its key
- **THEN** no file is written to `machine/ssh_keys/`

### Requirement: Migration of secure-note items
An existing item of type secure note with the fields `public_key` and `private_key` SHALL still be readable for restore. Publish and setup SHALL replace it with an SSH key item holding the same key and, once that item is created and read back with the same fingerprint, SHALL delete the old note (into the Bitwarden trash, not permanently).

#### Scenario: Old note present
- **WHEN** the host's item is a secure note with both fields
- **THEN** an SSH key item with the same key is created, read back, and the old note is moved to the Bitwarden trash

#### Scenario: New item cannot be confirmed
- **WHEN** creating the SSH key item fails or reading it back shows another fingerprint
- **THEN** the old note is kept and the problem is reported
