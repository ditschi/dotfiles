# ssh-host-keys Specification

## Purpose
Defines how every host gets one SSH key that is backed up whole in Bitwarden, restored on reinstall and generated when missing, and how the public keys of home hosts are versioned in the repository for authorized_keys.

## Requirements

### Requirement: Whole key backed up as a Bitwarden SSH key item
The host's key SHALL be stored as a Bitwarden item of type SSH key named `ssh/<class>/hosts/<hostname>`, with private key, public key and fingerprint. There SHALL be no option to store only the public key. The class SHALL be `home` or `work` from the profile. Only items of type SSH key SHALL be read; secure notes with the same name SHALL be ignored.

#### Scenario: Key uploaded
- **WHEN** setup uploads the key of a home host
- **THEN** the item `ssh/home/hosts/<hostname>` of type SSH key holds the private key, the public key and the fingerprint

#### Scenario: Old secure note present
- **WHEN** a secure note with the item's name exists and no SSH key item
- **THEN** the note is neither read nor changed, and the key is stored in a new SSH key item

### Requirement: Every host gets a key
With the feature `ssh-host-key`, `machine setup` SHALL, without asking and in this order: restore the key from the host's Bitwarden item when one exists and no local key is selected; otherwise upload the selected existing local key; otherwise generate an ed25519 key without passphrase on the host and upload it. Setup SHALL use the Bitwarden session it already has and SHALL NOT prompt for an extra unlock.

#### Scenario: Reinstalled host
- **WHEN** setup runs on a fresh install of a host that has an item in Bitwarden
- **THEN** its key is restored without a question and the host keeps its identity

#### Scenario: New host without a key
- **WHEN** setup runs on a host without a local key and without an item
- **THEN** an ed25519 key is generated on the host and uploaded, and the public key is printed with a hint to register it where needed

#### Scenario: Bitwarden not available
- **WHEN** setup runs without an unlocked Bitwarden session
- **THEN** no key is generated, restored or uploaded, and setup says that the next `machine update` or `machine setup` with Bitwarden finishes it

### Requirement: Key check during update
The manual `machine update` SHALL compare the host's key with its Bitwarden item only when a valid Bitwarden session is available without a prompt (environment or `~/.env.local`). A missing item SHALL be created with the local key without asking; a different key SHALL become an attention item. Without such a session it SHALL log a warning that says how to log in. It SHALL never generate or restore a key.

#### Scenario: Key not backed up
- **WHEN** `machine update` runs with a saved valid session and the host's key has no item
- **THEN** the item is created with the local key without a question

#### Scenario: Different key
- **WHEN** `machine update` runs with a saved valid session and the item holds another key
- **THEN** both keys stay unchanged and an attention item names both fingerprints

#### Scenario: No session
- **WHEN** `machine update` runs and no valid session is available without a prompt
- **THEN** no key check runs, nothing prompts, and a warning says that the SSH key was not checked and to log in with `machine env pull` in a terminal


### Requirement: Background update without Bitwarden
The background update SHALL NOT use Bitwarden; only the manual `machine update` checks the SSH key.

#### Scenario: Background update
- **WHEN** the background update runs
- **THEN** it does not call `bw`

### Requirement: Resolving a different key
When the local key and the item differ, `machine attention` and `machine ssh sync` SHALL show both fingerprints and ask which side wins: local (the item is overwritten with the local key), Bitwarden (the local key is renamed to `<key>.old-<YYYYMMDD>` and the item's key is written in its place) or later (nothing changes). Without a terminal nothing SHALL change.

#### Scenario: Local wins
- **WHEN** the user chooses the local key
- **THEN** the item holds the local key afterwards

#### Scenario: Bitwarden wins
- **WHEN** the user chooses the Bitwarden key
- **THEN** the old local private and public key are kept as `<key>.old-<YYYYMMDD>` and the item's key is in their place

#### Scenario: No terminal
- **WHEN** `machine ssh sync` runs without a terminal
- **THEN** both keys stay unchanged and the difference is reported

### Requirement: Rotating the key
`machine ssh rotate` SHALL generate a new ed25519 key without passphrase at `~/.ssh/id_ed25519_<hostname>`, keep a key already at that path as `<key>.old-<YYYYMMDD>`, select the new key, overwrite the Bitwarden item with it and, for the `home` class, update `machine/ssh_keys/<hostname>.pub`.

#### Scenario: Rotate
- **WHEN** a user runs `machine ssh rotate` with Bitwarden unlocked
- **THEN** the new key is selected and in the item, the old key file is kept as `.old-<YYYYMMDD>`, and the public key is printed with a hint to register it where needed

### Requirement: Existing keys are kept
Existing local keys SHALL keep their path, permissions and passphrase, and SHALL be selected in the current order: `MACHINE_SSH_KEY`, `id_ed25519`, `id_rsa`, a hostname key, a sole other candidate. Restoring in setup SHALL never overwrite an existing private key; only the explicit choice "Bitwarden wins" or `rotate` replaces a local key, keeping the old one as `<key>.old-<YYYYMMDD>`.

#### Scenario: Host with an existing key
- **WHEN** the host has a key and no item exists
- **THEN** that key is uploaded unchanged

#### Scenario: Restore with a local key present
- **WHEN** setup would restore a private key where one already exists
- **THEN** the existing key stays unchanged

### Requirement: Public keys of home hosts in the repository
For the `home` class, setup, `sync` and `rotate` SHALL write the public key to `machine/ssh_keys/<hostname>.pub` without a question and log a hint to commit it. Keys of the `work` class SHALL NOT be written to the repository. `authorized_keys` SHALL be filled only by the Ansible role `sshd_home` from `machine/ssh_keys/` for the hosts in `ssh_allow_from`; `machine` SHALL NOT read public keys from Bitwarden for `authorized_keys`.

#### Scenario: Apply with ssh_allow_from
- **WHEN** `machine apply` runs on a host with `ssh_allow_from: [homeserver]` and `machine/ssh_keys/homeserver.pub` exists
- **THEN** that key is in `authorized_keys` and no Bitwarden lookup happens

#### Scenario: Choosing ssh_allow_from
- **WHEN** setup offers hosts for `ssh_allow_from`
- **THEN** it offers the hosts with a file in `machine/ssh_keys/`

#### Scenario: Work host
- **WHEN** a work host uploads its key
- **THEN** no file is written to `machine/ssh_keys/`
