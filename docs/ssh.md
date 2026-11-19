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

## Reverse tunnels

The `jump` route of `ssh-route` goes through a reverse SSH tunnel that each home host or device keeps open to the jump host (oracle): `ssh -W localhost:<port> oracle` reaches the device's sshd on the port of its jump route. Tailscale stays the primary remote path; the tunnel is the fallback.

The ports exist only in the host list: the jump route of a block (`jump=oracle:2223`) is the port the device listens on, and the jump host allows exactly the jump routes that name it. `machine ssh add` suggests the next free port from 2223.

- **Jump host, feature `jump-host`** (oracle): a system user `tunnel` without a shell. Its `authorized_keys`, written whole by the role `jump_host`, has one line per jump route, `restrict,port-forwarding,permitlisten="127.0.0.1:<port>"`, with the key from [`machine/ssh_tunnel_keys/<alias>.pub`](../machine/ssh_tunnel_keys/) (devices without dotfiles) or `machine/ssh_keys/<alias>.pub` (hosts with dotfiles use their user key). An sshd `Match User tunnel` block in `/etc/ssh/sshd_config.d/50-jump-host.conf` allows only remote forwarding, no TTY, and ends a session that stops answering after about 90 s, so a reconnecting device gets its port back. The listeners are loopback-only; no firewall port is opened. The role reads the host list file written on the jump host, never Bitwarden, so a new device needs a manual `machine update` on oracle after the host list edit. A jump route without a key file is skipped with a warning.
- **Hosts with dotfiles, feature `ssh-tunnel`**: the systemd user unit `ssh-tunnel.service` runs `~/.local/bin/ssh-tunnel`, which reads the jump host and port from the host's own block (`HostKeyAlias` = short hostname) and runs `ssh -N -R 127.0.0.1:<port>:localhost:22 tunnel@oracle` without connection sharing (`ControlMaster=no`; with the shared default the foreground ssh would exit at once), with `ExitOnForwardFailure` and keep-alive. systemd restarts it 30 s after every exit; linger starts it at boot. Without a jump route it exits with status 78 and stays stopped. `machine update` enables or disables the unit with the feature.
- **Devices without dotfiles** (e.g. a NAS whose system cannot run the dotfiles): [`machine/ssh_tunnel/device-tunnel.sh`](../machine/ssh_tunnel/device-tunnel.sh) with its own key and a pinned host key of oracle, started by the DSM Task Scheduler; setup in [`machine/ssh_tunnel/README.md`](../machine/ssh_tunnel/README.md).

```bash
systemctl --user status ssh-tunnel         # client: running, last exit, log
journalctl --user -u ssh-tunnel -n 20
ss -ltn | grep '127.0.0.1:22[0-9][0-9]'    # on oracle: which tunnels are up
ssh -o ProxyCommand='ssh -W localhost:2223 oracle' homeserver true   # test the jump route alone
```

## Technical users (work)

Work hosts log in to the CI agents as technical users, with the key first and the password as fallback. The password is read live from Azure Key Vault, so nothing is typed or stored. Which users, and in which vault, is the key `AZKV_TECHUSERS` of the Bitwarden item `env/groups/work` (see [Secrets](secrets.md#technical-user-passwords-work-azure-key-vault)).

The `work` dotfile group links a thin `~/.local/bin/ssh` in front of the real `ssh`. It asks `ssh -G` which user the target resolves to; only when that user is in `AZKV_TECHUSERS` does it set `ssh-askpass-azkv` as askpass program, so ssh calls it only when it needs a password, that is, after key authentication failed. Every other connection runs the real `ssh` unchanged. `scp`, `rsync`, `git` and `ssh-copy-id` call `ssh` through `PATH` and behave the same. A `SSH_ASKPASS` that is already set (for example by an editor's remote feature) is not replaced.

The helper answers only password prompts that name that user (`user@host's password:`, `(user@host) Password:`); a jump host for another account, password-change prompts, host-key questions and passphrases are asked in the terminal. For these users the wrapper sets `NumberOfPasswordPrompts=1`, so a wrong password from Key Vault is sent only once. When Key Vault cannot be read (not logged in with `az login`, no VPN, no access), it says so in one line and asks for the password in the terminal.

The wrapper needs `~/.local/bin` before the real `ssh` in `PATH`; the login shells of the dotfiles do that. Check with `command -v ssh`.

To authorize the key of a technical user on an agent, run `ssh-copy-id` as that user; it uses the same password source:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_<techuser>.pub <techuser>@<agent>
```

A key that is already authorized is skipped. Always pass `-i`: without it `ssh-copy-id` installs every key of the agent and of `~/.ssh/id*.pub`, also personal ones, into the account of the technical user. The key authorizes this machine only; each machine with its own key repeats the step, and a re-imaged agent loses it, in which case the password fallback still works.

## SSH agent

The dotfiles never start an `ssh-agent`. An interactive bash or zsh keeps an existing `SSH_AUTH_SOCK` (agent forwarding with `ssh -A`, the GNOME session's agent); otherwise it uses `$XDG_RUNTIME_DIR/openssh_agent`, the socket of the systemd user unit `ssh-agent.socket` from `openssh-client`, when it exists; otherwise there is no agent. The keys have no passphrase, so `ssh` does not need one. Where you want an agent on a host without that socket, enable it with `systemctl --user enable --now ssh-agent.socket` or start one by hand with `eval "$(ssh-agent -s)"`.

Before this, every zsh login without an agent started its own, and none was ended. To list and end them:

```bash
pgrep -u "$USER" -ax ssh-agent        # leftovers show as "ssh-agent -s"; systemd and gcr run theirs with -D
pkill -u "$USER" -fx 'ssh-agent -s'    # ends only the leftovers
```
