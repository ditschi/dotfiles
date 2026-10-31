# secret-tools Specification

## Purpose
Defines the Bitwarden CLI, session handling and the Ansible Vault password.

## Requirements

### Requirement: Bitwarden CLI installed for the user
The Bitwarden CLI `bw` SHALL be installed for the user by `mise` on every host, as a tool of the `core` group, from the official Bitwarden release build for the host's CPU (x86_64 or aarch64). Its version and checksums SHALL be pinned in the repository's lockfile. When `machine` needs `bw` and it is missing, it SHALL install that pinned version, also before the dotfiles are linked.

#### Scenario: Setup
- **WHEN** the Bitwarden tooling is set up
- **THEN** `bw` is available on `PATH` from `mise`, and not from a download to `~/.local/bin`

#### Scenario: Raspberry Pi
- **WHEN** `machine setup` or `machine update` installs the tools on an aarch64 host
- **THEN** `bw` is the pinned arm64 build from the lockfile and `bw --version` prints the pinned version

#### Scenario: Fresh host before the dotfiles are linked
- **WHEN** `machine setup` runs on a host without `bw` and reaches the Bitwarden step before the dotfile groups are applied
- **THEN** the pinned `bw` is installed and the Bitwarden step continues in the same run

#### Scenario: Missing bw in env pull
- **WHEN** `machine env pull` runs in a terminal on a host without `bw` and the user accepts the install offer
- **THEN** the pinned `bw` is installed and the command continues with the Bitwarden login or unlock

### Requirement: Old self-installed bw is removed
When `mise` provides `bw`, `machine setup` and `machine update` SHALL remove a file `~/.local/bin/bw` and log its removal, so that it cannot take precedence over the pinned version. Other `bw` installations outside `~/.local/bin` SHALL be left unchanged.

#### Scenario: Host with an old download
- **WHEN** `~/.local/bin/bw` exists and `machine update` runs on a host where `mise` provides `bw`
- **THEN** `~/.local/bin/bw` is removed, the removal is logged and `bw` resolves to the `mise` build

#### Scenario: mise could not install bw
- **WHEN** `~/.local/bin/bw` exists and `mise` does not provide `bw`
- **THEN** `~/.local/bin/bw` is kept

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

### Requirement: A valid saved session suppresses Bitwarden prompts
`machine setup` SHALL read `~/.env.local` before it asks anything about Bitwarden, and SHALL NOT ask to configure, log in or unlock when the saved `BW_SESSION` is accepted by `bw`.

#### Scenario: Saved session is valid
- **WHEN** `~/.env.local` holds a `BW_SESSION` that `bw status` reports as unlocked and a user runs `machine setup`
- **THEN** no Bitwarden question is asked

### Requirement: Influx credentials in Bitwarden
The Influx credentials for Telegraf SHALL be kept in the Bitwarden item `influxdb-telegraf-write`. `machine setup`, `machine apply` and the apply step of `machine update` SHALL read it before Ansible runs when the host has `monitoring`.

#### Scenario: Setup of a private host with monitoring
- **WHEN** a user runs `machine setup` on a private host with `monitoring` and Bitwarden is unlocked
- **THEN** the item `influxdb-telegraf-write` is read before Ansible and Telegraf gets its output in the same run

#### Scenario: Host without monitoring
- **WHEN** the host does not have `monitoring`
- **THEN** the item is not read

### Requirement: Influx item layout
Custom fields named like the variables (`INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`, optional `INFLUX_TELEGRAF_CONFIG_BASE`, `INFLUXDB_USER`, `INFLUXDB_USER_PASSWORD`, `INFLUXDB_DB`) SHALL be used first. For a login item, the password SHALL serve as `INFLUX_TOKEN` and the first URI as `INFLUX_URL` when those fields are absent.

#### Scenario: Login item with a token as password
- **WHEN** `influxdb-telegraf-write` is a login item with a password, a URI and the fields `INFLUX_ORG` and `INFLUX_BUCKET`
- **THEN** Ansible gets the password as token and the URI as URL

#### Scenario: Field wins over login
- **WHEN** the item has both a login password and a field `INFLUX_TOKEN`
- **THEN** the field value is used as the token

### Requirement: Influx credentials stay out of the shell environment
The values of `influxdb-telegraf-write` SHALL reach only the Ansible run, through a file readable only by the user and removed when the command ends. They SHALL NOT be written to `~/.env`, `~/.env.host` or `~/.env.local`. Values set in the process environment SHALL still be used when the item is missing.

#### Scenario: After setup
- **WHEN** `machine setup` has read `influxdb-telegraf-write`
- **THEN** no env file contains `INFLUX_TOKEN` and the temporary file is gone

### Requirement: Missing Influx item does not block the run
When Bitwarden is locked, not installed or has no `influxdb-telegraf-write` item, the run SHALL continue without the credentials and log which item is missing. A run without a terminal SHALL NOT prompt for it.

#### Scenario: Item missing
- **WHEN** `machine apply` runs on a host with `monitoring` and the item does not exist
- **THEN** the run logs that `influxdb-telegraf-write` is missing, Ansible runs without the credentials and an existing Telegraf output is kept
