## ADDED Requirements

### Requirement: Password items in Bitwarden
The passwords that `get-password` serves SHALL be kept in Bitwarden Login items, with the password in the login password field and the item name matched exactly: the work account password in `login/work/<user>`, whose username is that user, and the local `sudo` password of a private host in `login/home/hosts/<hostname>`.

#### Scenario: Work account password
- **WHEN** the owner stores the work account password for the user `alice`
- **THEN** it is the login password of the Login item `login/work/alice` with the username `alice`

#### Scenario: Default user
- **WHEN** `get-password` is called without a username and reads the work account item
- **THEN** it reads `login/work/<user>` for the user that `id -un` prints

#### Scenario: Private host sudo password
- **WHEN** the owner stores the local `sudo` password of the private host `nas`
- **THEN** it is the login password of the Login item `login/home/hosts/nas`

#### Scenario: Similar names
- **WHEN** Bitwarden holds `login/work/alice-old` but no `login/work/alice`
- **THEN** no work account password is found for `alice`
