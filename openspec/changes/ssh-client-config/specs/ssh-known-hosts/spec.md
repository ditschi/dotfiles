# Spec Delta

## Purpose

Defines how the public sshd host keys of home hosts are versioned in the repository and turned into a managed known-hosts file on every host, so that home hosts are trusted without a first-connection prompt.

## ADDED Requirements

### Requirement: Host keys in the repository
The public ed25519 sshd host key of each managed home host SHALL be stored in `machine/ssh_host_keys/<name>.pub` as one line `<type> <key> <name>`. `<name>` SHALL be the short hostname for a host with a host profile, and the alias for a device without one. Only public keys SHALL be stored; private sshd host keys SHALL NOT be backed up.

#### Scenario: Host with a host profile
- **WHEN** the host key of the host `privatecloud` (alias `oracle`) is stored
- **THEN** it is in `machine/ssh_host_keys/privatecloud.pub` and the host block of `oracle` uses `HostKeyAlias privatecloud`

### Requirement: Hosts write their own host key
On a private host, `machine setup` and the manual `machine update` SHALL write the host's own public sshd host key to `machine/ssh_host_keys/<hostname>.pub` when the file is missing or differs, without a question, and SHALL log that the file must be pushed.

#### Scenario: Reinstalled home server
- **WHEN** a home server was reinstalled with a new sshd host key and `machine setup` runs
- **THEN** its file holds the new key and the change is listed as not pushed yet

### Requirement: Adding a device without dotfiles
`machine ssh known-hosts add <alias>` SHALL fetch the ed25519 host key from the address of the alias, show its fingerprint and write the file only after confirmation. When a file for the alias exists with another key, it SHALL show both fingerprints and default to keeping the existing key.

#### Scenario: New NAS
- **WHEN** a user runs `machine ssh known-hosts add nas` and confirms the fingerprint
- **THEN** `machine/ssh_host_keys/nas.pub` holds the key and the file is listed as not pushed yet

#### Scenario: Changed device key
- **WHEN** the device presents a key that differs from its file and the user presses Enter
- **THEN** the file is unchanged

### Requirement: Generated known-hosts file
On a private host, `machine apply`, including the background update, SHALL generate `~/.ssh/known_hosts.d/home` from all files in `machine/ssh_host_keys/`, one line per file keyed by its name, without Bitwarden. Hosts with another context SHALL NOT get the file.

#### Scenario: Key pushed from another host
- **WHEN** another host pushed a new file and the background update applies it
- **THEN** `~/.ssh/known_hosts.d/home` contains the new key

#### Scenario: Work host
- **WHEN** the dotfile groups are applied on a work host
- **THEN** `~/.ssh/known_hosts.d/home` is not created

### Requirement: Managed hosts are trusted without prompt
A connection to a home host whose host block sets `HostKeyAlias` to a name in the generated file SHALL be verified against that key, on every route and without a first-connection prompt. A differing key SHALL fail verification.

#### Scenario: New laptop
- **WHEN** a freshly set up private laptop runs `ssh homeserver` for the first time
- **THEN** ssh does not ask to confirm the host key
