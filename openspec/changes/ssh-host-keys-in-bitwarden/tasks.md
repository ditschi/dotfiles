# Tasks

## 1. Bitwarden SSH key items

- [ ] 1.1 Store the host key as an item of type SSH key (`type: 5`, private key, public key, fingerprint) named `ssh/<class>/hosts/<hostname>`; stop with both fingerprints when the item holds another key. Verify unit tests with a stubbed `bw` for create, same key (no change) and other key.
- [ ] 1.2 Remove `--private` from `machine ssh publish`; publish always stores the whole key. Verify `machine ssh --help` and the CLI tests.
- [ ] 1.3 Restore reads SSH key items and the old secure notes (`private_key`/`public_key` fields), never overwriting an existing private key. Verify unit tests for both item types and for an existing key.

## 2. Every host gets a key

- [ ] 2.1 With `ssh-host-key`, setup restores, else uploads the selected local key, else generates ed25519 without passphrase and uploads; keep the current selection order and leave existing keys unchanged. Verify unit tests for the three paths and for unattended setup without Bitwarden.
- [ ] 2.2 Migrate a secure-note item to an SSH key item with the same key and tell the user the old note can be deleted. Verify a unit test.

## 3. Public keys in the repository

- [ ] 3.1 For the `home` class, write `machine/ssh_keys/<hostname>.pub` in setup and publish and offer the commit; never for `work`. Verify unit tests for both classes.
- [ ] 3.2 Remove `apply_authorized_keys_from_bw` and its calls; `authorized_keys` comes only from the role `sshd_home`. Verify no `missing ssh/` message in an apply and the `sshd_home` role run in a container.
- [ ] 3.3 Offer the hosts with a file in `machine/ssh_keys/` for `ssh_allow_from` in setup. Verify a unit test.

## 4. Docs and checks

- [ ] 4.1 Rewrite the Readme section "SSH keys". Verify the text matches the behaviour.
- [ ] 4.2 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and `openspec validate ssh-host-keys-in-bitwarden --strict`. Verify all pass.
