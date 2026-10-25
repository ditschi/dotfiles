# Design

## Context

Today `ssh_keys.py` selects or generates a host key, publishes the public key as a field `public_key` of a secure note `ssh/<class>/hosts/<hostname>`, uploads the private key only with `--private`, restores it with `machine ssh restore`, and after Ansible adds the public keys of `ssh_allow_from` hosts from Bitwarden to `authorized_keys` (`apply_authorized_keys_from_bw`). The Ansible role `sshd_home` adds the same hosts' keys from `machine/ssh_keys/*.pub`. On the owner's vault (checked 2026-10-25) only the laptop has an item, a secure note with both fields; the repository has public keys for five hosts. See proposal.md for the motivation.

Bitwarden CLI 2026.8 creates SSH key items (`type: 5`, `sshKey: {privateKey, publicKey, keyFingerprint}`) through `bw create item`; it requires all three fields (`apps/cli/src/vault/create.command.ts`, `libs/common/src/models/export/ssh-key.export.ts`). Bitwarden generates SSH keys only in its graphical clients.

## Decisions

- **Always the whole key (owner decision).** A public-key-only backup cannot restore a host, so `publish` always stores the private key; the flag `--private` goes away. The SSH key item type keeps private key, public key and fingerprint together.
- **Generate on the host, then upload (owner decision).** `ssh-keygen -t ed25519` works on every host, including headless ones and without a Bitwarden GUI; the CLI cannot generate SSH keys. Restore comes first, so a reinstalled host keeps its identity.
- **No passphrase on generated keys (owner decision, option 1).** The background update and other unattended Git/SSH use must work without a prompt; at-rest protection comes from disk encryption. Rejected: a passphrase stored as a hidden field with automatic `ssh-add` into a persistent agent (needs a session-wide agent and an unlocked Bitwarden after every reboot; with the Bitwarden session saved in `~/.env.local` it adds little protection), and the Bitwarden desktop SSH agent (keys never on disk, but a locked app breaks the background `git fetch`, and it does not exist on headless hosts).
- **Public keys of home hosts in the repository, not in Bitwarden.** The repository is the only source of host profiles, and `ssh_allow_from` lives there; Ansible fills `authorized_keys` from `machine/ssh_keys/` without Bitwarden, also headless and for `--limit` runs. Bitwarden keeps the full key as backup only. Public keys are not secret; host names are already in `machine/hosts/`.
- **Setup (and bootstrap) provisions the key (owner decision).** A new host gets its key restored from Bitwarden or generated during setup, so bootstrap leaves every host with the feature `ssh-host-key` with a key that is backed up; existing keys that are not in Bitwarden yet are uploaded.
- **Ask before replacing a different key in Bitwarden (owner decision).** When the local key and the item differ, setup and publish show both fingerprints and ask, default no; unattended runs change nothing.
- **Update checks silently, reports through attention (owner decision).** `machine update` compares key and item only with a Bitwarden session that needs no prompt; a missing or different item becomes an attention item, resolved interactively via `machine`. The update itself never asks, generates, restores or uploads, so unattended runs stay quiet. Without a session nothing happens and nothing is printed.
- **Work keys stay out of the repository.** The repository is public and work hosts do not use `sshd-home`; the `work` class stays in Bitwarden only (`work-private-separation`).
- **Old note deleted after the migration (owner decision).** Once the SSH key item exists and reads back with the same fingerprint, the old secure note is deleted with `bw delete item` (without `--permanent`), so it goes to the Bitwarden trash and stays recoverable there for a while; no two items share the name afterwards. If the new item cannot be confirmed, the note stays.

## Risks / Trade-offs

- [Unencrypted key on disk] → mitigated by disk encryption; existing keys with a passphrase keep it.
- [Both items exist for a moment during the migration] → lookups pick the SSH key item by type when two items share the name; the note is deleted right after the new item is confirmed.
- [New key not registered at GitHub] → registering a generated key with GitHub (for example with `gh ssh-key add`) is out of scope; setup prints the public key and a hint.
