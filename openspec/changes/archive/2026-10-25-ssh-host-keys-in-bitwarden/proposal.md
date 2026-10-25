# Proposal

## Why

`machine ssh publish` stores only the public key in Bitwarden by default; the private key needs `--private`. A Bitwarden copy of a public key is no backup: after a reinstall the host still needs a new key, and every host that trusted the old one has to be updated. The public keys for `authorized_keys` also exist twice, in Bitwarden (`ssh/<class>/hosts/<host>`, read by `machine` after Ansible) and in the repository (`machine/ssh_keys/<host>.pub`, read by the Ansible role `sshd_home`); hosts that never ran `publish` produce `missing ssh/home/hosts/<host>` on every apply. Bitwarden has its own item type for SSH keys that holds private key, public key and fingerprint together.

## What Changes

- **BREAKING (CLI):** `machine ssh publish` and `machine ssh restore` are removed. `machine ssh` keeps two actions: `sync` resolves a difference between the local key and the Bitwarden item, `rotate` replaces the host's key with a new one.
- With the feature `ssh-host-key`, `machine setup` (and therefore bootstrap) provisions the key without asking whenever Bitwarden is available: it restores the host's key from its Bitwarden item, otherwise uploads the existing local key, otherwise generates an ed25519 key on the host (no passphrase) and uploads it. The key is stored as a Bitwarden item of type SSH key.
- `machine update` uploads the key without asking when the item is missing and a Bitwarden session works without a prompt. A different key becomes an attention item. Without such a session it logs a warning that says how to log in to Bitwarden. The background job does not touch Bitwarden.
- A difference between the local key and the item is never resolved automatically: `machine attention` or `machine ssh sync` asks which side wins. Old local keys are kept as `<key>.old-<date>`.
- For the `home` class, the public key is written to `machine/ssh_keys/<hostname>.pub` without a question, with a hint to commit it. `authorized_keys` is filled only by Ansible from the repository; `machine` no longer reads public keys from Bitwarden after Ansible.
- `machine setup` offers the hosts with a key in `machine/ssh_keys/` for `ssh_allow_from`, instead of the hosts published in Bitwarden.
- Existing secure-note items are not read or migrated; the owner removes them by hand.

## Capabilities

### New Capabilities
- `ssh-host-keys`: one SSH key per host, backed up as a Bitwarden SSH key item, restored on reinstall, generated when missing; public keys of home hosts versioned in the repository for `authorized_keys`.

### Modified Capabilities
- None. `work-private-separation` keeps the key classes `home` and `work`.

Affected profiles: hosts with the feature `ssh-host-key` (default on private profiles). Work machines keep their keys in the `work` class in Bitwarden only.

## Impact

- `machine_cli/ssh_keys.py`, `machine_cli/machine` (`ssh` actions), `machine_cli/profile.py` (`ssh_allow_from` candidates), `machine_cli/commands.py`, `machine_cli/updates.py`, `machine_cli/attention.py`, `machine/ssh_keys/`, tests, Readme section "SSH keys".
- Bitwarden: new items of type SSH key named `ssh/<class>/hosts/<hostname>`; old secure notes are removed by hand.
