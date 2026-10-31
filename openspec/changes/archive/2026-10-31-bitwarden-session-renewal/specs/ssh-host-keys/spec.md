# Spec Delta

## MODIFIED Requirements

### Requirement: Background update without Bitwarden
The background update SHALL NOT use Bitwarden; only the manual `machine update` checks the SSH key. When the host expects Bitwarden (see the capability `secret-tools`), the background update MAY call `bw status` to notice an expired session, and SHALL make no other `bw` call.

#### Scenario: Background update
- **WHEN** the background update runs on a host that does not expect Bitwarden
- **THEN** it does not call `bw`

#### Scenario: Background update with a saved session
- **WHEN** the background update runs on a host with a saved session
- **THEN** `bw status` is its only `bw` call

### Requirement: Key check during update
The manual `machine update` SHALL compare the host's key with its Bitwarden item only when a valid Bitwarden session is available, from the environment, `~/.env.local`, or renewed in a terminal (see "Expired session is renewed in a terminal" in `secret-tools`). A missing item SHALL be created with the local key without asking; a different key SHALL become an attention item. Without such a session it SHALL log a warning that says how to log in. It SHALL never generate or restore a key.

#### Scenario: Key not backed up
- **WHEN** `machine update` runs with a saved valid session and the host's key has no item
- **THEN** the item is created with the local key without a question

#### Scenario: Different key
- **WHEN** `machine update` runs with a saved valid session and the item holds another key
- **THEN** both keys stay unchanged and an attention item names both fingerprints

#### Scenario: No session
- **WHEN** `machine update` runs and no valid session is available without a prompt
- **THEN** no key check runs, nothing prompts, and a warning says that the SSH key was not checked and to log in with `machine env pull` in a terminal

#### Scenario: Expired saved session in a terminal
- **WHEN** `machine update` runs in a terminal and the saved session is expired
- **THEN** the session is renewed first and the key check runs with it
