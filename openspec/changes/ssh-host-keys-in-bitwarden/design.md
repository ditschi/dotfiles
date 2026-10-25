# Design

## Context

Today `ssh_keys.py` selects or generates a host key, publishes the public key as a field `public_key` of a secure note `ssh/<class>/hosts/<hostname>`, uploads the private key only with `--private`, restores it with `machine ssh restore`, and after Ansible adds the public keys of `ssh_allow_from` hosts from Bitwarden to `authorized_keys` (`apply_authorized_keys_from_bw`). The Ansible role `sshd_home` adds the same hosts' keys from `machine/ssh_keys/*.pub`. On the owner's vault (checked 2026-10-25) only the laptop has an item, a secure note with both fields; the repository has public keys for five hosts. See proposal.md for the motivation.

Bitwarden CLI 2026.8 creates SSH key items (`type: 5`, `sshKey: {privateKey, publicKey, keyFingerprint}`) through `bw create item`; it requires all three fields (`apps/cli/src/vault/create.command.ts`, `libs/common/src/models/export/ssh-key.export.ts`). Bitwarden generates SSH keys only in its graphical clients.

## Decisions

- **Always the whole key (owner decision).** A public-key-only backup cannot restore a host, so `publish` always stores the private key; the flag `--private` goes away. The SSH key item type keeps private key, public key and fingerprint together.
- **Generate on the host, then upload (owner decision).** `ssh-keygen -t ed25519` works on every host, including headless ones and without a Bitwarden GUI; the CLI cannot generate SSH keys. Restore comes first, so a reinstalled host keeps its identity.
- **No passphrase on generated keys (owner decision, option 1).** The background update and other unattended Git/SSH use must work without a prompt; at-rest protection comes from disk encryption. Rejected: a passphrase stored as a hidden field with automatic `ssh-add` into a persistent agent (needs a session-wide agent and an unlocked Bitwarden after every reboot; with the Bitwarden session saved in `~/.env.local` it adds little protection), and the Bitwarden desktop SSH agent (keys never on disk, but a locked app breaks the background `git fetch`, and it does not exist on headless hosts).
- **Public keys of home hosts in the repository, not in Bitwarden.** The repository is the only source of host profiles, and `ssh_allow_from` lives there; Ansible fills `authorized_keys` from `machine/ssh_keys/` without Bitwarden, also headless and for `--limit` runs. Bitwarden keeps the full key as backup only. Public keys are not secret; host names are already in `machine/hosts/`.
- **Work keys stay out of the repository.** The repository is public and work hosts do not use `sshd-home`; the `work` class stays in Bitwarden only (`work-private-separation`).
- **No deletion in the vault.** Migration creates the new item and leaves the old secure note; the user deletes it.

## Risks / Trade-offs

- [Unencrypted key on disk] → mitigated by disk encryption; existing keys with a passphrase keep it.
- [Item name reused by a new type] → before creating the SSH key item, the old note is renamed or the new item gets the same name and the old one is recognised by type; the implementation picks one and the restore reads both.
- [New key not registered at GitHub] → registering a generated key with GitHub (for example with `gh ssh-key add`) is out of scope; setup prints the public key and a hint.

## Open Questions

- Should the old secure note be renamed (for example with a suffix `(old)`) when the SSH key item is created, so two items with the same name do not exist side by side?
