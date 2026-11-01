# SSH

Per-host SSH keys in Bitwarden, `authorized_keys` for the home fleet and the SSH client config.

## SSH keys (home / work separated)

One key per host, backed up whole (private key, public key, fingerprint) as a Bitwarden item of type **SSH key**:

- Home: `ssh/home/hosts/<hostname>`
- Work: `ssh/work/hosts/<hostname>`

With the feature `ssh-host-key`, `machine setup` (and so bootstrap) handles the key without asking, using the Bitwarden session setup already has:

1. no local key, but an item in Bitwarden → the key is restored (a reinstalled host keeps its identity);
2. an existing local key → it is uploaded unchanged;
3. neither → an ed25519 key without passphrase is generated (`~/.ssh/id_ed25519_<hostname>`) and uploaded. Register it where needed, for example `gh ssh-key add`.

Existing keys keep their path, permissions and passphrase. Selection order: `MACHINE_SSH_KEY`, `id_ed25519`, `id_rsa`, the hostname key, a sole other candidate; only when several keys make the choice unclear does interactive setup ask, and an ambiguous choice changes nothing. The choice is cached locally. Without an unlocked Bitwarden nothing is generated, restored or uploaded.

`machine update` (the manual one) uploads the key when the item is missing and a Bitwarden session works without a prompt (environment or `~/.env.local`). Without such a session it warns that the key was not checked; log in with `machine env pull` in a terminal. The background job never uses Bitwarden. Only items of type SSH key are read; old secure notes with the same name are ignored.

**Different keys** on the host and in Bitwarden are never resolved automatically: setup and update keep both and list the difference in `machine attention`. There, or with `machine ssh sync`, you choose: `local` (overwrite the item), `bitwarden` (replace the local key; the old one is kept as `<key>.old-<YYYYMMDD>`) or `later`.

**authorized_keys:** for the `home` class, the public key is written to [`machine/ssh_keys/<hostname>.pub`](../machine/ssh_keys/) without a question; commit and push it. Work keys never go into the repository. The role `sshd_home` adds the keys of the hosts in `ssh_allow_from` (same class) from there; `machine` does not read public keys from Bitwarden. Setup offers the hosts with a file in `machine/ssh_keys/` for `ssh_allow_from`.

```bash
machine ssh sync              # host and Bitwarden differ: choose which key wins
machine ssh rotate            # new key at ~/.ssh/id_ed25519_<hostname>, old one kept, item overwritten
```

The manual `machine update` also keeps the repository files current without Bitwarden: `machine/ssh_keys/<hostname>.pub` holds only the selected key, and [`machine/ssh_host_keys/<hostname>.pub`](../machine/ssh_host_keys/) the host's sshd key. Changed files that are not pushed yet show up in `machine attention`, which offers to commit and push them.

## SSH client config

`~/.ssh/config` links to [`home/core/.ssh/config`](../home/core/.ssh/config). ssh takes the first value of each option, so the layers come in this order:

1. `~/.ssh/config.local`: this host only, never versioned or overwritten (like `~/.gitconfig.local`).
2. `~/.ssh/config.d/20-home` or `20-work`: the host list of the context, ready `ssh_config` text in the Bitwarden secure note `ssh/home/config` or `ssh/work/config`. Setup, the manual update and `machine ssh pull` write it after `ssh -G` accepts it; the background update leaves it alone. Addresses, users and ports never go into the repository.
3. `~/.ssh/config.d/90-legacy`: hosts of the hand-written config the link replaced (kept as `~/.ssh/config.pre-dotfiles`) that neither layer above defines. `machine attention` walks through them.
4. Shared defaults: keep-alive, connection sharing (`~/.ssh/cm`, 10 minutes; after a network change `ssh -O exit <host>`), `IdentitiesOnly`, readable known hosts.

Host blocks added by hand to the generated list are kept in a "local only" section; `machine attention` offers to add them to Bitwarden, move them to `config.local`, remove or skip them.

**Home hosts** use one alias everywhere. `ssh-route` (in `~/.local/bin`) is the `ProxyCommand` and tries `lan`, then `ts` (Tailscale, only when logged in and the peer is online), then `jump` (the reverse tunnel on the jump host; on the jump host itself the local port):

```
Host homeserver
  User ditschi
  HostKeyAlias homeserver
  ProxyCommand ~/.local/bin/ssh-route %k lan=192.168.1.4:22 jump=oracle:2223
```

The home network is learned, not configured: on an unknown network `ssh-route` compares the host key at the LAN address with the managed key of the alias and remembers the gateway in `~/.cache/ssh-route/networks`. A replaced home router is learned the same way; `machine attention` then offers to drop the old entry.

**Managed host keys** (private hosts): `machine apply` writes `~/.ssh/known_hosts.d/home` from [`machine/ssh_host_keys/`](../machine/ssh_host_keys/), so home hosts are trusted without a first-connection prompt on every route. Hosts with dotfiles write their own file; devices without dotfiles are added with `machine ssh known-hosts add <alias>`. Work hosts use the normal first-connection prompt.

```bash
machine ssh add [alias]              # guided: address, user, port, routes; list or config.local; login test
machine ssh edit                     # host list in $EDITOR, checked by ssh before saving
machine ssh remove <alias>           # host block and managed host key
machine ssh pull                     # write the host list from Bitwarden now
machine ssh known-hosts add <alias>  # fetch, confirm and store a device's host key
```

`machine setup` offers to add the host itself to the host list of its context.
