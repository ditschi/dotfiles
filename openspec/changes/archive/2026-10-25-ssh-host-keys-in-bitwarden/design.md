# Design

## Context

Today `ssh_keys.py` selects or generates a host key, publishes the public key as a field `public_key` of a secure note `ssh/<class>/hosts/<hostname>`, uploads the private key only with `--private`, restores it with `machine ssh restore`, and after Ansible adds the public keys of `ssh_allow_from` hosts from Bitwarden to `authorized_keys` (`apply_authorized_keys_from_bw`). The Ansible role `sshd_home` adds the same hosts' keys from `machine/ssh_keys/*.pub`. On the owner's vault (checked 2026-10-25) only the laptop has an item, a secure note with both fields; the repository has public keys for five hosts. See proposal.md for the motivation.

Bitwarden CLI 2026.8 creates SSH key items (`type: 5`, `sshKey: {privateKey, publicKey, keyFingerprint}`) through `bw create item`; it requires all three fields (`apps/cli/src/vault/create.command.ts`, `libs/common/src/models/export/ssh-key.export.ts`). Bitwarden generates SSH keys only in its graphical clients.

## Decisions

- **Always the whole key (owner decision).** A public-key-only backup cannot restore a host, so the private key is always stored; the flag `--private` goes away. The SSH key item type keeps private key, public key and fingerprint together.
- **Generate on the host, then upload (owner decision).** `ssh-keygen -t ed25519` works on every host, including headless ones and without a Bitwarden GUI; the CLI cannot generate SSH keys. Restore comes first, so a reinstalled host keeps its identity.
- **No passphrase on generated keys (owner decision, option 1).** The background update and other unattended Git/SSH use must work without a prompt; at-rest protection comes from disk encryption. Rejected: a passphrase stored as a hidden field with automatic `ssh-add` into a persistent agent (needs a session-wide agent and an unlocked Bitwarden after every reboot; with the Bitwarden session saved in `~/.env.local` it adds little protection), and the Bitwarden desktop SSH agent (keys never on disk, but a locked app breaks the background `git fetch`, and it does not exist on headless hosts).
- **Public keys of home hosts in the repository, not in Bitwarden.** The repository is the only source of host profiles, and `ssh_allow_from` lives there; Ansible fills `authorized_keys` from `machine/ssh_keys/` without Bitwarden, also headless and for `--limit` runs. Bitwarden keeps the full key as backup only. Public keys are not secret; host names are already in `machine/hosts/`.
- **Automatic wherever Bitwarden is available (owner decision).** Setup (and therefore bootstrap) and the manual `machine update` restore, upload or generate without asking; setup uses the session it already has and does not prompt for an extra unlock. Without Bitwarden nothing is generated or uploaded.
- **Warning when update has no Bitwarden session (owner decision).** The user should know that the key is not checked and that a Bitwarden login may be needed; the warning names the command to log in (`machine env pull` in a terminal).
- **A different key is a decision, never automatic (owner decision).** Setup and update leave both keys unchanged and report an attention item. `machine attention` and `machine ssh sync` ask which side wins: local (overwrite the item), Bitwarden (replace the local key) or later.
- **`machine ssh` only for sync and rotate (owner decision, option A2).** Restore and upload happen in setup and update, so `publish` and `restore` go away. `sync` opens the same dialog as the attention item; `rotate` generates a new ed25519 key, uploads it over the item and updates the repository public key.
- **Old local key kept as a file (owner decision, option C1).** When Bitwarden wins or a key is rotated, the old private and public key are renamed to `<key>.old-<YYYYMMDD>`; the item is overwritten.
- **Background job without Bitwarden (owner decision, option B1).** Only the manual `machine update` uses the vault; the background job never does.
- **Repository public key without a question (owner decision, option D1).** Like the host profile with `--yes`: the file is written, committing stays manual with a hint.
- **No secure-note handling in the CLI (owner decision).** Only the laptop has an old note; the owner removes it by hand. The CLI reads only SSH key items.
- **Work keys stay out of the repository.** The repository is public and work hosts do not use `sshd-home`; the `work` class stays in Bitwarden only (`work-private-separation`).

## Risks / Trade-offs

- [Unencrypted key on disk] → mitigated by disk encryption; existing keys with a passphrase keep it.
- [Old secure note shares the name with the new item until removed by hand] → the CLI selects the item of type SSH key.
- [New key not registered at GitHub] → registering a generated or rotated key with GitHub (for example with `gh ssh-key add`) is out of scope; setup and rotate print the public key and a hint.

## Assumptions

- The selection question for several local keys stays in interactive setup; it appears only when the choice is unclear.
- `rotate` always creates the new key at `~/.ssh/id_ed25519_<hostname>`; a different key used before (for example `id_rsa`) stays on disk but is no longer selected.
