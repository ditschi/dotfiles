# Proposal

## Why

`machine ssh publish` stores only the public key in Bitwarden by default; the private key needs `--private`. A Bitwarden copy of a public key is no backup: after a reinstall the host still needs a new key, and every host that trusted the old one has to be updated. The public keys for `authorized_keys` also exist twice, in Bitwarden (`ssh/<class>/hosts/<host>`, read by `machine` after Ansible) and in the repository (`machine/ssh_keys/<host>.pub`, read by the Ansible role `sshd_home`); hosts that never ran `publish` produce `missing ssh/home/hosts/<host>` on every apply. Bitwarden has its own item type for SSH keys that holds private key, public key and fingerprint together.

## What Changes

- **BREAKING (CLI):** `machine ssh publish` always uploads the whole key as a Bitwarden item of type SSH key; the `--private` flag is removed.
- With the feature `ssh-host-key`, `machine setup` (and therefore bootstrap) makes sure every host has a key: it restores the host's key from Bitwarden when an item exists, otherwise uploads an existing local key, otherwise generates an ed25519 key on the host (no passphrase) and uploads it.
- When the local key differs from the Bitwarden item, setup and publish show both fingerprints and ask whether to update the item (default no); without a terminal nothing is changed.
- `machine update` checks the key silently when a Bitwarden session is available without a prompt, and reports a missing or different item as an attention item; without a session it does nothing.
- For the `home` class, the public key is written to `machine/ssh_keys/<hostname>.pub` in the repository, with the same commit offer as the host profile. `authorized_keys` is filled only by Ansible from the repository; `machine` no longer reads public keys from Bitwarden after Ansible.
- `machine setup` offers the hosts with a key in `machine/ssh_keys/` for `ssh_allow_from`, instead of the hosts published in Bitwarden.
- Existing secure-note items (`public_key`/`private_key` fields) are read for restore and migrated to an SSH key item; once the new item is confirmed, the old note is moved to the Bitwarden trash.

## Capabilities

### New Capabilities
- `ssh-host-keys`: one SSH key per host, backed up as a Bitwarden SSH key item, restored on reinstall, generated when missing; public keys of home hosts versioned in the repository for `authorized_keys`.

### Modified Capabilities
- None. `work-private-separation` keeps the key classes `home` and `work`.

Affected profiles: hosts with the feature `ssh-host-key` (default on private profiles). Work machines keep their keys in the `work` class in Bitwarden only.

## Impact

- `machine_cli/ssh_keys.py`, `machine_cli/machine` (`ssh publish` options), `machine_cli/profile.py` (`ssh_allow_from` candidates), `machine_cli/commands.py`, `machine/ssh_keys/`, tests, Readme section "SSH keys".
- Bitwarden: new items of type SSH key named `ssh/<class>/hosts/<hostname>`; the old secure notes go to the trash after the migration.
