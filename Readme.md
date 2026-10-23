# Dotfiles + machine setup

One repo for shell dotfiles and machine bootstrap. Git is the source of truth: files under `$HOME` are symlinks into this repo. Commit and push changes from any host; other hosts run `machine update`.

Behaviour and its motivation live in [openspec/specs/](openspec/specs) and the archived changes; open investigations are in [openspec/investigations/](openspec/investigations); new features are planned with [OpenSpec](openspec/config.yaml); agent rules in [AGENTS.md](AGENTS.md).

## Quick start (on the new host, no control node)

```bash
git clone https://github.com/ditschi/dotfiles.git ~/dotfiles
cd ~/dotfiles
./bootstrap
```

Or in one step, which clones the repository to `~/dotfiles` (override with `DOTFILES_DIR`; needs `git` and a public repository):

```bash
curl -fsSL https://raw.githubusercontent.com/ditschi/dotfiles/main/bootstrap | bash
```

Bootstrap links `~/.local/bin/machine` to `machine_cli/machine` in the checkout. An existing clone is used as it is; update it with `machine update`.

Hosts that still have the CLI deployed by chezmoi: run `~/dotfiles/bootstrap` (or `chezmoi apply`) once after pulling this change; `git pull` alone then no longer breaks `machine`.

Non-interactive:

```bash
./bootstrap --profile home-laptop --yes
./bootstrap --profile work-machine --yes
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
| Bring other hosts up to date | `machine update` (pulls, runs only the affected steps) |
| Packages/system | `machine update --system` or `machine apply` |
| Apply a host profile remotely | `machine apply --limit homeserver` |
| Full setup / change features | `machine setup` (saved answers as defaults) |
| Save host profile to the repo | `machine profile save` |
| Status / drift | `machine status` / `machine profile show` |
| Inventory (vault) | `machine inventory edit ansible/inventory/hosts.yml` |
| `~/.env` from Bitwarden | `machine env pull` |
| SSH public key to Bitwarden | `machine ssh publish` |
| Install collections | `ansible-galaxy collection install -r ansible/requirements.yml` |

`machine update` only runs what changed upstream: `chezmoi apply` for added/removed files under `home/`, Ansible when `ansible/**` changed, a profile sync when `machine/hosts/**` changed. Local edits are kept; the update stops only when a locally edited file is also changed upstream or history diverged (`--force` stashes overlapping edits, merges, restores them). `machine update --check [--json]` shows the plan without changing anything. The background job (`machine update --auto`, every 6 hours via the user timer) applies home-only changes on its own when the checkout has no local changes after the resolvers: it fast-forwards to just before the first commit that touches `ansible/**` or this host's profile, runs `chezmoi apply` when needed, then runs the zsh health check; if zsh no longer starts it reverts to the previous revision, does not retry that revision and shows needs-attention. Everything from the first system commit on stays pending for a manual `machine update`. `machine setup` and `machine update` also enable systemd linger for the user (best effort, not in containers; on failure they print `sudo loginctl enable-linger <user>`), so the timer runs on headless hosts without a login. Managed blocks added to `~/.bashrc` by other tools are moved to `~/.bashrc-local` (sourced at the end of `.bashrc`).

The background update check (`dotfiles-update-check-job`) and `machine update` write `~/.dotfiles-update-state` (`state`, `reason`, `revision`). Interactive zsh and bash show it in the prompt (Starship `env_var` module; without Starship, at the right of the zsh prompt or as a `PS1` prefix in bash), re-read before every prompt without forking: `⬆ dotfiles update` (run `machine update`), `↻ reload shell` (an update was applied after this shell started; run `reload`), `⚠ dotfiles: check` (needs attention, e.g. diverged history; a line with the reason is also printed at shell start). A shell started after the update shows nothing. `machine status` prints the state, the reason and the fix.

`~/.zshrc-local` is only for genuine single-host exceptions and is not in git.

### Shell: prompt and plugins

Both shells use [Starship](https://starship.rs) with the shared `~/.config/starship.toml` (all profiles). The prompt character shows the shell: a green `❯` in zsh, a purple `❯` in bash; `🐳` marks a container, and a failed command shows in the status segment. Without Starship both shells fall back to a plain prompt (directory and `❯`).

zsh plugins are managed by [antidote](https://antidote.sh): edit `~/.zsh/plugins.txt` (one plugin per line; order matters) and open a new shell — the generated `~/.cache/zsh/plugins.zsh` is rebuilt and missing plugins are cloned to `~/.local/share/antidote`. `antidote update` updates them. The prompt appears first; completion (`compinit`), fzf-tab, history-substring-search, autosuggestions and fast-syntax-highlighting load right after it via zsh-defer. Tools such as fzf, zoxide, eza, fd, delta and Starship come from mise; their shell init is cached in `~/.cache/zsh` and regenerated when the binary changes.

bash is a fallback with the same tools: Starship, fzf (Ctrl+R), zoxide (`z`), LS_COLORS and the git helpers (`git open`, `git recent`, `git recall`) from the antidote checkouts, Up/Down prefix search, Esc Esc for `sudo`, and pasting commands with a leading `$ ` or `❯ `.

Data of the former zinit/Powerlevel10k setup is not removed automatically. After the switch it can be deleted with:

```bash
rm -rf ~/.local/share/zinit ~/.cache/p10k-* ~/.cache/gitstatus
```

Before bash hands over to zsh, a startup health check runs. If zsh fails or loads only partly, the shell stays in bash and prints one line with the reason. The result is cached until the zsh config, the zsh binary or `~/.preferred-shell` changes, or dotfiles are updated. After fixing the cause, run `zsh-recheck` to clear the cache and check again.

### Node and LLM tools

`machine apply` provisions user-local NVM and Node LTS (including npm) on every
profile, including containers. An existing NVM default with Node 22 or newer is
kept; older defaults are upgraded to LTS with their global packages migrated.
No system Node installation is removed. Bash and zsh load NVM on startup.

`machine setup` offers `claude-code` and `copilot-cli` in its feature picker.
New private host profiles default to Claude Code; `work-machine` defaults to both.
Containers have neither CLI enabled by default.
Existing saved host features remain authoritative: rerun `machine setup` and
select the desired CLIs, then save the host profile to roll them out.
Existing CLI installations are preserved; missing CLIs are installed globally
in the NVM default runtime without sudo. Authentication remains a manual step.

OpenSpec is installed automatically when either CLI is selected or an existing
Claude, Copilot, Codex, Gemini, Aider or Ollama command is found, even when both
features are disabled.

The runtime requires an architecture supported by upstream Node LTS. Original
ARMv6 Pi Zero hosts cannot run current official Node binaries; provisioning
reports a failure rather than silently substituting an obsolete runtime.

### Git config

- `~/.gitconfig` → symlink into the repo, identical on all hosts. `git config --global alias.x ...` lands there directly → commit, done.
- `~/.gitconfig.local` → host-local, not in git, included after the shared settings. chezmoi creates it once from the profile (`work-machine` → work user, otherwise private) and never overwrites it. Signing key, `safe.directory`, credentials and proxy go here.
- Owner rules at the end of `~/.gitconfig` override the host default by remote URL: github.com `bosch-*`/`bosch_*`, GHES and Bitbucket → `~/.config/git/work.gitconfig`, any other github.com owner → `~/.config/git/private.gitconfig`. Each sets identity plus the GitHub credential username and helper.
- `git-credential-env VAR` serves tokens from the environment or `~/.env` (`GITHUB_TOKEN`, `BDC_GITHUB_TOKEN`, `GITHUB_PRIVATE_TOKEN`) and never stores them. `~/.netrc` entries for the same host take precedence in curl, so keep GitHub out of it.
- Single repo with a different identity: `git user-work` / `git user-private` (repo-local include of the same snippet), undo with `git user-unset-local`; show: `git user-show`.
- `machine update` and `machine commit` move host-only entries from the shared config into `~/.gitconfig.local`. A key that is absent locally moves, an equal value is dropped from the shared file, and a different local value is a conflict that `machine update` asks about (non-interactive runs keep both and leave the shared file dirty). Repeated values are preserved. Backups live under `~/.local/share/machine/local-overrides-backup/`. Text added to `~/.bashrc` is handled the same way: known text is removed silently, new text is moved only when you select it, and moved text stands between `# machine-local begin/end` markers in `~/.bashrc-local`.
- The installed pre-commit hook does the same before an ordinary Git commit. If it changes the shared file, review and stage the cleaned file, then commit again.
- CI runs `python3 -m machine_cli.local_overrides --check` and fails on committed host-only entries or invalid config. Hooks also run read-only when `CI=true`. Restricted keys include user identity/signing keys, signing settings, `safe.*`, `credential.*`, `http.*`, `https.*` and `core.sshCommand`; `user.useConfigOnly` remains shared.

### Project Containers

`sde` runs the current project's `.devcontainer/sde.sh` when present, forwarding
arguments and its exit status. Non-executable scripts run through Bash. Without
that file, the shared Bash launcher is used. `sdx` calls that launcher in extended
mode, mounting the selected dotfiles checkout, plugin/apt caches, host HOME and
per-project history. Set `SDE_CONTAINER_HOME` if the container HOME differs from
the host HOME. Initialization runs before Compose; extended setup runs before
post-start and the shell or supplied command. Interactive sessions prefer zsh,
falling back to Bash.

Existing images can be reused or rebuilt, and interactive callers can attach to
existing project containers. `sdx` only offers containers created in extended
mode. Rebuilding starts a new container rather than attaching to one using the
old image. One-off commands reuse the image but always run in a fresh container,
without prompts or forced TTY allocation. To force a rebuild, invoke
`command sde --extended --rebuild -- <cmd> [args...]` (omit `--extended` for minimal
mode). The shell wrappers pass arguments as commands; shell expressions should
be explicit, e.g. `sdx bash -lc 'echo ready && make test'`.

## Layout

```
bootstrap                 # clones if piped, installs uv, links machine, calls machine setup
machine_cli/              # the machine CLI: `machine` script + package (not chezmoi-managed)
home/                     # chezmoi source, mode=symlink
machine/
  hosts/                  # versioned host answers (<hostname>.yml)
  ssh_keys/               # public host keys for ssh_allow_from
ansible/
  workstation.yml         # packages + monitoring + sshd + stylus
  homelab.yml             # stub — stacks live in the homelab repo
  requirements.yml        # ansible.posix (+ Galaxy notes)
  inventory/local.yml     # always localhost
  inventory/hosts.example.yml
  profiles/               # feature defaults per profile
  roles/
    monitoring/           # Telegraf agent configs
    sshd_home/            # port 5115 + authorized_keys
    stylus_touch_guard/   # Yoga stylus/touch (ex helpers-and-automation)
    touch_device/         # GNOME touch extensions (TouchUp, Screen Rotate)
    thinkpad_tuning/      # charge thresholds, power profile, S3, zram, tablet OSK
tests/                    # unit + Docker/CI
```

`machine_cli/machine` is a [PEP 723](https://peps.python.org/pep-0723/)
script (shebang `uv run --script`, Python 3.11–3.13) — its dependencies (click, rich,
PyYAML) are declared inline and resolved by [uv](https://astral.sh/uv) on first
run, no manual venv. `./bootstrap` installs `uv` itself if it's missing. `~/.local/bin/machine`
is a symlink to it, so the checkout is found by resolving the link and can be anywhere; because
chezmoi does not deploy the CLI, a plain `git pull` cannot leave it half updated. `machine_cli/`
(code) is not to be confused with `machine/` (host data).

`machine --debug <command>` (or `DEBUG=1`) prints every command the CLI
runs and passes `-v` to Ansible.

The script itself only defines the command line. The implementation is the package
`machine_cli/` next to it:

| Module | Content |
| --- | --- |
| `core` | constants (profiles, features) and pure helpers |
| `system` | everything touching the outside world (`run`, `have`, tty, hostname); tests replace these here |
| `profile` | local profile, versioned host files, prompts |
| `tools` | bootstrap tools, git / ansible / chezmoi runners |
| `bitwarden` | `~/.env`, per-host SSH keys, authorized_keys |
| `commands` | setup, apply, update, status, commit, push |
| `machine` | the `Machine` class combining the modules above |

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

`machine apply` locally: if Ansible or the health check fails, the previous `profile.yml` is restored. The health check fails when the zsh startup check fails or when `chezmoi managed` cannot read the config or source (unprivileged checks only; telegraf is a warning). The same restore applies to the apply step of `machine update`. If the profile changed, Ansible runs again with the old state. Remote (`--limit`): no auto-revert — fix the profile in git and apply again.

The recovery Ansible run only happens when syncing the host profile changed it;
an unchanged profile is restored without repeating the same failed command.
Package and system changes are not transactionally rolled back.

Managed work machines may allow only specific sudo commands. The workstation
playbook requires approval to execute Ansible modules as root, not just permission
to run selected APT commands. A correct sudo password does not grant that approval.
If fact gathering reports "not allowed to execute", stop and contact the machine
administrator for an approved deployment route. `--no-become` only suppresses the
password prompt; it does not disable the playbook's root tasks. Dotfile and
environment management can remain active without applying system roles.

## Secrets / Bitwarden

On real hosts, setup installs the **CLI** (`bw`) to `~/.local/bin` (not the GUI snap).
Interactive `machine setup` offers Bitwarden configuration and login before
fetching secrets. For an unauthenticated CLI, it asks for the HTTPS server URL
(including self-hosted servers). Already authenticated accounts keep their server.
Passwords and two-factor codes are entered locally through the CLI.

After a successful unlock and sync, a separate, default-no prompt offers to save
`BW_SESSION`, `NODE_EXTRA_CA_CERTS`, and `NODE_USE_ENV_PROXY` in `~/.env.local`
with mode 600. Existing unrelated content is preserved, and repeated setup replaces
these exports rather than duplicating them. The helper first tries the existing
network settings. Only on a certificate trust error does it offer Ubuntu's system
CA bundle; only on a DNS/connection error with an HTTPS proxy configured does it
offer Node environment-proxy support. Neither workaround is added automatically,
and TLS verification stays enabled. Kerberos authenticates the proxy but does not
configure application proxy support or certificate trust.
Existing literal local exports are loaded without executing the file.

Saving the token grants local processes vault access while it remains valid;
it is never uploaded to Bitwarden or printed. Unlock again after expiry.
Declining storage keeps the session only for the setup process.
`--yes` / non-interactive setup never prompts or persists unlock tokens.
Without an unlocked vault, environment fetching and key uploads are skipped.

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

The shell loads exactly these files, in order (later assignments win):

| File | Contents | Ownership |
| --- | --- | --- |
| `~/.env` | Class-shared and profile Bitwarden items | Generated |
| `~/.env.host` | This host's Bitwarden item | Generated |
| `~/.env.local` | Local overrides, certificate/proxy exports, `BW_SESSION` | Local, never overwritten |

These files are **not** in git and are not symlinks. Before replacing changed
generated files, their previous contents are backed up with owner-only
permissions under `~/.local/share/machine/env-backup/`. Other `~/.env.*` files
are not loaded automatically.

Keep `BW_SESSION` local: it is needed to unlock the vault before fetching items,
and may expire. Pull refuses vault items containing a `BW_SESSION` assignment.
Existing local override files are left byte-for-byte unchanged.

Local-only keys are retained in a new `~/.env.local` when safe. If that overlay
already exists and lacks the keys, or the old file contains complex shell
content, the pull leaves both generated files unchanged, exits with an error, and prints the live and backup paths
for manual review. Existing overlays are never overwritten; secret values are
not printed in warnings.

Each profile belongs to groups (`ENV_GROUPS` in `machine_cli/core.py`): `work-machine` → `work`; `home-laptop` → `private`; `home-server` → `private`, `server`; `rpi` → `private`, `server`, `iot`; `rpi-zero` → `private`, `iot`; `container` → none.

Item names (secure note, or login with note + custom fields). Later items and custom fields win for identical keys:

| Layer | Item name | Example |
| --- | --- | --- |
| Groups (in order) | `env/groups/<group>` | `env/groups/work`, `env/groups/private`, `env/groups/server`, `env/groups/iot` |
| This host | `env/hosts/<hostname>` | `env/hosts/ditschi-ThinkPad-L13-Yoga-Gen-2` |
| Infra | `ansible-vault` | vault password |

**Folders in Bitwarden** (personal vault) or collections (organization), same names:

- `work` — work laptops only (`env/groups/work`, SSH/VPN)
- `home` — private machines and shared home secrets
- `iot` — Pis / Zero (`env/groups/iot`, `env/hosts/rpi-zero-1`)
- `infra` — `ansible-vault`, host password hashes, not for shell `.env`

Contents of an `env/…` item:

- **Notes:** existing `.env` as text (`KEY=value`, one line per variable)
- **Custom fields** (hidden): frequently changed passwords, e.g. `VPN_PASSWORD` — override the same key from the notes

Existing `.env` contents can be transferred manually into an approved work-vault
secure note named `env/groups/work`, or the host item for narrower scope.
Secrets should never be committed to dotfiles. The current pull does not resolve
references to other Bitwarden items: custom-field values are literal values.
Vault folders are organizational labels, not enforced access boundaries; namespaced
item selection does not replace vault/organization permissions.

Don't put work secrets in `env/home-*`. Home hosts never query `env/work-*`.

```bash
machine env status    # which items exist
machine env pull      # write ~/.env and ~/.env.host; preserve ~/.env.local
```

### SSH keys (home / work separated)

Optional per host: `~/.ssh/id_ed25519_<hostname>`. Public key as text field `public_key` in Bitwarden:

Setup reuses existing local private keys without changing their paths,
permissions or passphrases. With multiple keys, interactive setup asks which to
reuse; unattended setup prefers `id_ed25519`, then `id_rsa`, then an existing
hostname key or sole other candidate. Ambiguous selection skips creation and
publication. Set `MACHINE_SSH_KEY` to select a path explicitly; the choice is
cached locally. A key is generated only when none exists. A missing public-key
file may be derived without a passphrase prompt; otherwise the original key is
kept and publication is skipped. Private upload remains opt-in, and restore
refuses to overwrite an existing private key.

- Home: `ssh/home/hosts/<hostname>`
- Work: `ssh/work/hosts/<hostname>`

In `profile.yml`, `ssh_allow_from:` controls which hostnames (same class) may SSH into **this** machine. Ansible/setup only fetches public keys of the same class. Private keys only after explicit confirmation.

```bash
machine ssh publish           # upload public key
machine ssh publish --private # including private key
machine ssh restore           # restore private key
```

## Profiles / features

`work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`

Features (selected during bootstrap, answers stored in `profile.yml`): `zsh-full`, `fonts`, `starship`, `desktop`, `gnome`, `cosmic`, `docker`, `kerberos`, `azure-cli`, `monitoring`, `unattended-upgrades`, `etckeeper`, `syncthing`, `tailscale`, `ssh-host-key`, `stylus-touch-guard`, `thinkpad-tuning`, `touch-device`, `sshd-home`

Home profiles get `monitoring` (Telegraf) by default. Config names live **only** in `ansible/group_vars/all.yml` → `monitoring_by_profile` and are resolved in `tasks/resolve_monitoring.yml` (not in the CLI). Remote configs via `INFLUX_TELEGRAF_CONFIG_BASE` / `INFLUX_URL` from Bitwarden are preferred; otherwise files under `ansible/roles/monitoring/files/`.

Yoga/convertible (L13): feature `stylus-touch-guard` → role `stylus_touch_guard`. Previously: [helpers-and-automation](https://github.com/ditschi/helpers-and-automation) (**archived / deprecated**).
ThinkPad laptops: features `thinkpad-tuning` → role `thinkpad_tuning` and `touch-device` → role `touch_device`, see [docs/thinkpad-l13-yoga-gen2.md](docs/thinkpad-l13-yoga-gen2.md).

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
| Ansible | apt, `/etc`, Telegraf, stylus-touch-guard, sshd-home |
| mise | User-space tools without root (`home/core/.config/mise/conf.d/*.toml`, pinned by `mise.lock`) |
| Inventory | Reachability only — no features |

Work modules (`01_work.zsh`) are only linked for profile `work-machine`.

Fresh setup uses the shell's work-account naming rule
(`^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$`), so `dci2lr` defaults to
`work-machine`. Explicit `--profile` / `MACHINE_PROFILE_NAME` choices and saved
host profiles take precedence outside Docker. In Docker (`/.dockerenv` or
`MACHINE_IN_DOCKER=1`) the profile is always `container`, in the CLI and the
shell, and `WORK_SETUP` stays off; set `MACHINE_PROFILE_OVERRIDE=<profile>` to
test another profile in a container.

Working Azure CLI and GitHub CLI installations are kept, including their
authentication and package sources. Docker provisioning preserves an existing
provider instead of replacing it with `docker.io`; only a missing,
provider-compatible Compose package is added. Unmanaged providers may need
manual Compose setup. The work profile does not enable Docker by default.

User-space tools (`fzf`, `zoxide`, `eza`, `fd`, `starship`, `jq`, `tmux`, `gh`,
`yazi`, Node, the LLM CLIs and OpenSpec, Azure CLI) come from mise fragments in
`home/core/.config/mise/conf.d/`. Versions are pinned in `home/core/.config/mise/mise.lock`
and `.mise/locks/` next to it; regenerate them with
`mise lock --global --platform linux-x64,linux-arm64` after a fragment change.
A tool declared in two fragments, or in a fragment and an Ansible package list,
fails `python3 -m machine_cli.mise_check` (pre-commit and CI).

## Tests

### Automated

```bash
uvx nox                         # compile + unit + Ansible lint + Docker smoke (without full APT), in uv venvs
uvx nox -l                      # list sessions; run one with `uvx nox -s tests -- -k handoff`
DOTFILES_TEST_INSECURE_TLS=1 uvx nox -s docker   # test containers skip TLS verification (hosts that intercept TLS)
# automatic on work machines; DOTFILES_TEST_INSECURE_TLS=0 forces verification there
pytest tests/unit -q            # logic incl. apply revert, host YAML schema (needs tests/requirements.txt)
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
```
