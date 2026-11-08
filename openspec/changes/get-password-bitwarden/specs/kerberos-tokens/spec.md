## MODIFIED Requirements

### Requirement: Password lookup
`get-password [user]` SHALL print the owner's password from the env files (`$PASSWORD`, or `PASSWORD` read from `~/.env`, `~/.env.host` and `~/.env.local` with the shell loader's rules when it is not in the environment). Only when no env password exists SHALL it read its other sources, Bitwarden and the GNOME keyring (`secret-tool`). It SHALL NOT prompt, open an unlock dialog or block on a locked keyring or vault.

#### Scenario: Password in the env files
- **WHEN** `PASSWORD` is set in `~/.env` and the keyring and Bitwarden hold a different password
- **THEN** `get-password` prints the value from the env files

#### Scenario: Called from a service
- **WHEN** a systemd user service without the shell environment calls `get-password` and `~/.env` sets `PASSWORD`
- **THEN** `get-password` prints that value

#### Scenario: Password in the keyring
- **WHEN** no env password exists, Bitwarden gives no password, and the keyring is unlocked and holds the password
- **THEN** `get-password` prints the keyring password

#### Scenario: Keyring not usable
- **WHEN** the keyring gives no password and `$PASSWORD` is set
- **THEN** `get-password` prints the value of `$PASSWORD`

#### Scenario: Locked keyring
- **WHEN** no env password exists, Bitwarden gives no password and the keyring is locked
- **THEN** `get-password` exits non-zero within a few seconds and no unlock dialog appears

## ADDED Requirements

### Requirement: Bitwarden password source
When Bitwarden can be read without a prompt, `get-password` SHALL read the password from the login password field of the matching item (spec `secret-tools`, "Password items in Bitwarden"). A missing `bw`, a locked or unreachable vault or a missing item SHALL make it skip Bitwarden without an error. It SHALL NOT prompt for, log in to or unlock Bitwarden, and SHALL give up on Bitwarden within a bounded time.

#### Scenario: Password in Bitwarden
- **WHEN** no env password exists, the keyring gives no password, and Bitwarden is unlocked and holds the matching item
- **THEN** `get-password` prints the item's login password

#### Scenario: Vault locked
- **WHEN** no env password exists and the Bitwarden vault is locked
- **THEN** `get-password` asks for no master password, skips Bitwarden and continues with its remaining sources

#### Scenario: Item missing
- **WHEN** Bitwarden is unlocked but holds no matching item
- **THEN** `get-password` skips Bitwarden without an error message about the vault and continues with its remaining sources

#### Scenario: bw not installed
- **WHEN** `bw` is not on `PATH`
- **THEN** `get-password` behaves as without Bitwarden

#### Scenario: Non-interactive caller
- **WHEN** `kinit-pw` runs from the user timer and Bitwarden cannot be read without a prompt
- **THEN** no prompt appears and the call returns within a bounded time
