# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Old self-installed bw is removed
When `mise` provides `bw`, `machine setup` and `machine update` SHALL remove a file `~/.local/bin/bw` and log its removal, so that it cannot take precedence over the pinned version. Other `bw` installations outside `~/.local/bin` SHALL be left unchanged.

#### Scenario: Host with an old download
- **WHEN** `~/.local/bin/bw` exists and `machine update` runs on a host where `mise` provides `bw`
- **THEN** `~/.local/bin/bw` is removed, the removal is logged and `bw` resolves to the `mise` build

#### Scenario: mise could not install bw
- **WHEN** `~/.local/bin/bw` exists and `mise` does not provide `bw`
- **THEN** `~/.local/bin/bw` is kept
