# Dotfiles + machine setup

One repo for shell dotfiles and machine bootstrap. Git is the source of truth: files under `$HOME` are symlinks into this repo. Commit and push changes from any host; other hosts run `machine update`.

## Quick start (on the new host, no control node)

```bash
git clone https://github.com/ditschi/dotfiles.git ~/dotfiles
cd ~/dotfiles
./bootstrap
```

Non-interactive:

```bash
./bootstrap --profile home-laptop --yes
./bootstrap --profile work-laptop --yes
./bootstrap --profile rpi-zero --yes --no-become
```

From the laptop to a reachable device:

```bash
./bootstrap --limit rpi-zero-1 --profile rpi-zero
```

## Day to day

| Action | Command |
| --- | --- |
| Change an alias for all hosts | Edit the file in `$HOME` (it is the repo file), `machine commit -m "..." && machine push` |
| Bring other hosts up to date | `machine update` (pulls host profile, applies on drift) |
| Packages/system | `machine update --system` or `machine apply` |
| Apply a host profile remotely | `machine apply --limit homeserver` |
| Full setup / change features | `machine setup` (saved answers as defaults) |
| Save host profile to the repo | `machine profile save` |
| Layout from `main` → chezmoi | `machine migrate` |
| Undo migration | `machine rollback` |
| Status / drift | `machine status` / `machine profile show` |
| Inventory (vault) | `machine inventory edit ansible/inventory/hosts.yml` |
| `~/.env` from Bitwarden | `machine env pull` |
| SSH public key to Bitwarden | `machine ssh publish` |
| Install collections | `ansible-galaxy collection install -r ansible/requirements.yml` |

Uncommitted local changes block `machine update` (unless `--force`).

`~/.zshrc-local` is only for genuine single-host exceptions and is not in git.

### Git config

- `~/.gitconfig` → symlink into the repo, identical on all hosts. `git config --global alias.x ...` lands there directly → commit, done.
- `~/.gitconfig.local` → host-local, not in git, included last (wins). chezmoi creates it once from the profile (`work-laptop` → work user, otherwise private) and never overwrites it. Signing key, `safe.directory`, credentials and proxy go here.
- Single repo with a different identity: `git user-work` / `git user-private`; show: `git user-show`.
- The pre-commit hook `gitconfig-no-host-settings` rejects `user.*`, `gpg.*`, `safe.*`, `credential.*`, `http.*` etc. in the shared file.

## Layout

```
bootstrap                 # calls machine setup
home/                     # chezmoi source, mode=symlink
machine/
  hosts/                  # versioned host answers (<hostname>.yml)
  ssh_keys/               # public host keys for ssh_allow_from
ansible/
  workstation.yml         # packages + user_tools + monitoring + sshd + stylus
  homelab.yml             # stub — stacks live in the homelab repo
  requirements.yml        # ansible.posix (+ Galaxy notes)
  inventory/local.yml     # always localhost
  inventory/hosts.example.yml
  profiles/               # feature defaults per profile
  roles/
    monitoring/           # Telegraf agent configs
    sshd_home/            # port 5115 + authorized_keys
    stylus_touch_guard/   # Yoga stylus/touch (ex helpers-and-automation)
    user_tools/           # starship, fonts
docs/                     # deprecation notes etc.
tests/                    # unit + Docker/CI
```

Profile cache: `~/.config/machine/profile.yml` (not in git).  
**Source of truth per host:** [`machine/hosts/<hostname>.yml`](machine/hosts/) — features and `ssh_allow_from`. chezmoi config: `~/.config/chezmoi/chezmoi.yaml`.

### Versioning and pushing host profiles

```bash
# On the host, once (or after changing features):
machine setup                 # interactive
machine profile save          # → machine/hosts/$(hostname -s).yml
machine commit -m "host profile" && machine push

# Laptop: allow SSH from this laptop to the server
# edit machine/hosts/homeserver.yml → ssh_allow_from: [this-hostname]
machine commit -m "allow laptop on homeserver" && machine push

# On the server:
machine update                # pull → sync profile → apply on drift

# Or from the laptop without logging in to the server:
machine apply --limit homeserver
```

`machine apply` locally: if Ansible or the health check fails, the previous `profile.yml` is restored and Ansible runs again with the old state. Remote (`--limit`): no auto-revert — fix the profile in git and apply again.

## Secrets / Bitwarden

On real hosts, setup installs the **CLI** (`bw`) to `~/.local/bin` (not the GUI snap). Interactively, the wizard only asks: "Log in to Bitwarden now?" Without a login, `~/.env` and key uploads are skipped.

### Inventory

- Copy real hosts/IPs to `ansible/inventory/hosts.yml` and encrypt it with Ansible Vault.
- Vault password lives in Bitwarden, item name `ansible-vault` (override: `MACHINE_VAULT_BW_ITEM`).
- Roles and package lists stay plain text.

```bash
cp ansible/inventory/hosts.example.yml ansible/inventory/hosts.yml
machine inventory encrypt ansible/inventory/hosts.yml
```

### `~/.env` from Bitwarden

Change the password in Bitwarden, then run `machine env pull` or `machine update` on the host. Bitwarden never pushes to devices — the host fetches the current state on apply (`bw sync`). Without an unlocked `bw`, the last `~/.env` stays in place.

`~/.env` is **not** in git and not a symlink. Overlay for true snowflakes: `~/.env.local` (never overwritten). Before the first overwrite, a backup is written to `~/.local/share/machine/env-backup/`.

Item names (secure note, or login with note + custom fields). Later items and custom fields win for identical keys:

| Layer | Item name | Example |
| --- | --- | --- |
| Class shared | `env/<class>-shared` | `env/work-shared`, `env/home-shared`, `env/iot-shared` |
| Profile | `env/profiles/<profile>` | `env/profiles/work-laptop` |
| This host | `env/hosts/<hostname>` | `env/hosts/ditschi-ThinkPad-L13-Yoga-Gen-2` |
| Infra | `ansible-vault` | vault password |

**Folders in Bitwarden** (personal vault) or collections (organization), same names:

- `work` — work laptops only (`env/work-shared`, `env/profiles/work-laptop`, SSH/VPN)
- `home` — private machines and shared home secrets
- `iot` — Pis / Zero (`env/iot-shared`, `env/hosts/rpi-zero-1`)
- `infra` — `ansible-vault`, host password hashes, not for shell `.env`

Contents of an `env/…` item:

- **Notes:** existing `.env` as text (`KEY=value`, one line per variable)
- **Custom fields** (hidden): frequently changed passwords, e.g. `VPN_PASSWORD` — override the same key from the notes

Don't put work secrets in `env/home-*`. Home hosts never query `env/work-*`.

```bash
machine env status    # which items exist
machine env pull      # write ~/.env
```

### SSH keys (home / work separated)

Optional per host: `~/.ssh/id_ed25519_<hostname>`. Public key as text field `public_key` in Bitwarden:

- Home: `ssh/home/hosts/<hostname>`
- Work: `ssh/work/hosts/<hostname>`

In `profile.yml`, `ssh_allow_from:` controls which hostnames (same class) may SSH into **this** machine. Ansible/setup only fetches public keys of the same class. Private keys only after explicit confirmation.

```bash
machine ssh publish           # upload public key
machine ssh publish --private # including private key
machine ssh restore           # restore private key
```

## Profiles / features

`work-laptop`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`

Features (selected during bootstrap, answers stored in `profile.yml`): `zsh-full`, `fonts`, `starship`, `desktop`, `gnome`, `cosmic`, `docker`, `kerberos`, `work-cli`, `monitoring`, `unattended-upgrades`, `syncthing`, `tailscale`, `ssh-host-key`, `stylus-touch-guard`, `sshd-home`

Home profiles get `monitoring` (Telegraf) by default. Config names live **only** in `ansible/group_vars/all.yml` → `monitoring_by_profile` and are resolved in `tasks/resolve_monitoring.yml` (not in the CLI). Remote configs via `INFLUX_TELEGRAF_CONFIG_BASE` / `INFLUX_URL` from Bitwarden are preferred; otherwise files under `ansible/roles/monitoring/files/`.

Yoga/convertible (L13): feature `stylus-touch-guard` → role `stylus_touch_guard`. Previously: [helpers-and-automation](https://github.com/ditschi/helpers-and-automation) (**archived / deprecated**).

SSH home fleet: feature `sshd-home` → port **5115** (`roles/sshd_home`) + `authorized_keys` from [`machine/ssh_keys/`](machine/ssh_keys/) for entries in `ssh_allow_from`.

### Galaxy vs. local roles

| Need | Decision |
| --- | --- |
| Telegraf | **Local** `roles/monitoring` (Influx env + `machine/*` fragments). Galaxy `dj-wasabi.telegraf` / `boutetnico.telegraf` possible, but heavier and a worse fit. |
| Docker | **apt** `docker.io` / `compose-v2`. Later optionally `geerlingguy.docker` or collection `community.docker`. |
| SSH keys/port | **Local** `sshd_home` + collection `ansible.posix` (`authorized_key`). |
| Stylus | **Local** (ex helpers-and-automation). |

Collections: `ansible-galaxy collection install -r ansible/requirements.yml`.

### Architecture (short)

| Layer | Responsible for |
| --- | --- |
| `machine/hosts/*.yml` | Desired state (profile, features) |
| `machine` CLI | Orchestration, UX, secrets, git, calling chezmoi |
| chezmoi | Dotfiles |
| Ansible | apt, `/etc`, Telegraf, user_tools, stylus-touch-guard, sshd-home |
| Inventory | Reachability only — no features |

Work modules (`01_work.zsh`) are only linked for profile `work-laptop`.

## Migration (from the old root layout)

On a host still running `main` with symlinks to `~/dotfiles/.zshrc`:

```bash
cd ~/dotfiles
git fetch && git checkout feat/machine-setup   # or main, once merged
./bootstrap          # or: machine migrate
```

`machine update` detects broken/old root symlinks and asks interactively whether to run a full setup. Non-interactively it aborts with the hint `machine migrate --yes`.

Backup under `~/.local/share/machine/migration/<stamp>/`. Rollback:

```bash
machine rollback
# or: ~/.local/share/machine/rollback.sh
```

Hosts **already** on the chezmoi layout don't need a second migration — just `machine update`, or `machine setup` when features change.

## Revert

```bash
~/.local/share/machine/rollback.sh
# or manually:
cd ~/dotfiles
git checkout <old-sha>            # listed in rollback.sh / migration meta.json
python3 install.py --update --force
```

The `install.py` of **that** commit recreates the root symlinks. After that, the old update path runs.

## Legacy commands

`python3 install.py` remains a wrapper around `machine setup` / `machine update`.

## Tests

### Automated

```bash
./tests/run.sh                  # unit + Docker smoke (without full APT)
pytest tests/unit -q            # logic incl. apply revert, host YAML schema
pytest tests/integration -m "docker and not apt and not apt_gnome"
pytest tests/integration -m apt # rpi-zero APT + machine/hosts/ci-rpi-zero.yml
pytest tests/integration -m apt_gnome  # home-laptop APT + ci-home-laptop.yml (~10+ min)
ansible-lint ansible/*.yml      # locally / in CI on changes under ansible/ or machine/hosts/
ansible-galaxy collection install -r ansible/requirements.yml
```

CI (`.github/workflows/verify.yml`):

- Unit + Ansible syntax (amd64 + arm)
- Docker matrix of all profiles (without APT)
- Clean install from `machine/hosts/ci-container.yml`
- APT + Ansible from `machine/hosts/ci-rpi-zero.yml` and `ci-home-laptop.yml`
- **ansible-lint + host YAML validation** only when `ansible/**` or `machine/hosts/**` (or similar) changed

**Deliberately not in CI:** real Pi hardware, Kerberos against the work KDC, Cosmic session, real `bw login`/2FA, real Influx.

### Manual (Compose)

```bash
docker compose -f tests/compose.yaml run --rm shell
# inside the container:
./bootstrap --profile home-laptop          # with prompts
./bootstrap --profile home-laptop --yes    # quiet
machine setup                              # previous answers preselected
machine update                             # only bring up to date

docker compose -f tests/compose.yaml run --rm migrate
# prepared old symlinks → prompt "Run full setup / migration now?" / machine migrate
```
