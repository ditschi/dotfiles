# Tasks

## 1. Bitwarden SSH key items

- [x] 1.1 Store the host key as an item of type SSH key (`type: 5`, private key, public key, fingerprint) named `ssh/<class>/hosts/<hostname>`; read only SSH key items and ignore secure notes. Verify unit tests with a stubbed `bw` for create, same key (no change), other key (no change, attention item) and a secure note with the same name.
- [x] 1.2 Replace `machine ssh publish|restore` with `machine ssh sync|rotate`. Verify `machine ssh --help` and the CLI tests.

## 2. Automatic provisioning

- [x] 2.1 With `ssh-host-key`, setup restores, else uploads the selected local key, else generates ed25519 without passphrase and uploads, without a question and without an extra unlock prompt; keep the selection order and leave existing keys unchanged. Verify unit tests for the three paths and for setup without Bitwarden.
- [x] 2.2 The manual `machine update` creates a missing item without asking, reports a different key as attention item, and without a session logs a warning naming `machine env pull`; the background update does not call `bw`. Verify unit tests for missing item, different key, no session (warning, no prompt) and the background update.
- [x] 2.3 Resolve a difference in `machine attention` and `machine ssh sync`: local wins, Bitwarden wins (old key kept as `<key>.old-<YYYYMMDD>`), later; without a terminal nothing changes. Verify unit tests for the three answers and for no terminal.
- [x] 2.4 `machine ssh rotate`: new ed25519 key at `id_ed25519_<hostname>`, a key there kept as `.old-<YYYYMMDD>`, new key selected, item overwritten, repository key updated. Verify a unit test.

## 3. Public keys in the repository

- [x] 3.1 For the `home` class, write `machine/ssh_keys/<hostname>.pub` without a question in setup, sync and rotate and log a hint to commit; never for `work`. Verify unit tests for both classes.
- [x] 3.2 Remove `apply_authorized_keys_from_bw` and its calls; `authorized_keys` comes only from the role `sshd_home`. Verify no `missing ssh/` message in an apply and the `sshd_home` role run in a container.
- [x] 3.3 Offer the hosts with a file in `machine/ssh_keys/` for `ssh_allow_from` in setup. Verify a unit test.

## 4. Docs and checks

- [x] 4.1 Rewrite the Readme section "SSH keys". Verify the text matches the behaviour.
- [x] 4.2 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and `openspec validate ssh-host-keys-in-bitwarden --strict`. Verify all pass.
