# Spec Delta

## Purpose

Keeps the Bitwarden login items of the technical users equal to Azure Key Vault, which is always the current source, so that Bitwarden stays usable for the browser.

## ADDED Requirements

### Requirement: Key Vault wins over Bitwarden
`machine secrets sync` SHALL, for each user in `AZKV_TECHUSERS`, read the secret from Key Vault and compare it with the password of the existing Bitwarden login item named like the user. When they differ it SHALL set the item's password to the Key Vault value; when they are equal it SHALL change nothing.

#### Scenario: Outdated item
- **WHEN** the Bitwarden item `ci-user-a` holds an older password than Key Vault
- **THEN** the item's password equals the Key Vault password afterwards and the log says that `ci-user-a` was updated

#### Scenario: Already equal
- **WHEN** the passwords are equal
- **THEN** no Bitwarden write happens

### Requirement: Existing items only
The sync SHALL NOT create items. A user without a matching login item, or with several, SHALL be reported by name and left alone.

#### Scenario: Item missing
- **WHEN** no Bitwarden item is named `ci-user-b`
- **THEN** the sync reports that item as missing, creates nothing and continues with the other users

### Requirement: Only with az and Bitwarden
The sync SHALL run only when `az` has a valid login that can read the vault and Bitwarden has a usable session. Otherwise it SHALL write nothing and say which of the two is missing. The background update SHALL NOT run it.

#### Scenario: Bitwarden locked without a terminal
- **WHEN** `machine update` runs without a usable Bitwarden session
- **THEN** the sync is skipped with a line naming Bitwarden, and the update continues

#### Scenario: Background update
- **WHEN** the background update runs
- **THEN** neither `az` nor `bw` is called for the sync

### Requirement: Sync as part of the manual update
The manual `machine update` SHALL run the sync before the env pull on a host where `AZKV_TECHUSERS` is set, so that env references to the Bitwarden items resolve to the synced passwords. A failed sync SHALL NOT make the update fail.

#### Scenario: Update on a work host
- **WHEN** a user runs `machine update` on a work host with the mapping and both tools available
- **THEN** the Bitwarden items of the technical users equal Key Vault afterwards

#### Scenario: Reference to the item
- **WHEN** `env/groups/work` sets `KEY={{bw:<user>/password}}` and Key Vault holds a newer password
- **THEN** `~/.env` holds the Key Vault password after the same update

#### Scenario: Bitwarden not unlocked yet
- **WHEN** the update runs in a terminal and Bitwarden is locked
- **THEN** the login or unlock is asked once before the sync, and the env pull reuses it

#### Scenario: Sync raises an error
- **WHEN** the sync stops with an error, for example a failing `bw`
- **THEN** the update warns, continues and does not fail

#### Scenario: Host without the mapping
- **WHEN** `AZKV_TECHUSERS` is not set
- **THEN** the update neither calls `az` nor mentions the sync

### Requirement: Missing az login needs attention
When the sync could not read Key Vault because `az` is not logged in or the vault is unreachable, it SHALL record an attention item, and `machine attention` SHALL offer to run `az login` and the sync again. A successful sync SHALL clear the item.

#### Scenario: Expired az login
- **WHEN** the manual update finds the `az` login expired
- **THEN** `machine attention` lists an Azure item with the question `Log in now (az login)?`

#### Scenario: Next successful sync
- **WHEN** a later sync reads Key Vault
- **THEN** the item is gone

#### Scenario: Vault behind a firewall
- **WHEN** Key Vault answers that the client address is not allowed
- **THEN** the same item is recorded, because the vault is out of reach

### Requirement: Outcome is reported
A sync that reached Key Vault SHALL end with one line that names how many items were updated, were already equal and could not be synced, so that a silent success is distinguishable from a skipped sync.

#### Scenario: Nothing to change
- **WHEN** every Bitwarden password already equals Key Vault
- **THEN** the sync prints that no item was updated and how many were already equal

### Requirement: Passwords never appear in output
The sync SHALL log user names, item names and outcomes only, and SHALL NOT write a password to a file, a log or a command line.

#### Scenario: Updated item
- **WHEN** an item is updated
- **THEN** the output names the user and says `updated`, and no output line contains the password
