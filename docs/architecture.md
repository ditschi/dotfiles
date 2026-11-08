# Architecture

The `machine` CLI, where host state lives, and which layer is responsible for what.

## machine CLI

`machine_cli/machine` is a [PEP 723](https://peps.python.org/pep-0723/)
script (shebang `uv run --script`, Python 3.11–3.13) — its dependencies (click, rich,
PyYAML) are declared inline and resolved by [uv](https://astral.sh/uv) on first
run, no manual venv. `./bootstrap` installs `uv` itself if it's missing. `~/.local/bin/machine`
is a symlink to it, so the checkout is found by resolving the link and can be anywhere; because
the dotfile tool does not deploy the CLI, a plain `git pull` cannot leave it half updated. `machine_cli/`
(code) is not to be confused with `machine/` (host data).

`machine --debug <command>` (or `DEBUG=1`) prints every command the CLI
runs and passes `-v` to Ansible.

The script itself only defines the command line. The implementation is the package
`machine_cli/` next to it:

| Module | Content |
| --- | --- |
| `core` | constants (contexts, devices, features) and pure helpers |
| `system` | everything touching the outside world (`run`, `have`, tty, hostname); tests replace these here |
| `features` | the feature table: defaults, menu, dotfile groups |
| `profile` | host config (context, device, features), applied copy, prompts |
| `tools` | bootstrap tools, git / ansible runners |
| `dotfiles`, `mise_tools`, `mise_check`, `terminal_fonts` | dotfile groups (`mise dot`), tool install, fragment checks, terminal fonts |
| `bw_client`, `env_pull`, `ssh_keys` | Bitwarden client, `~/.env`, per-host SSH keys |
| `syncthing_ignores` | shared Syncthing ignore rules: `.stglobalignore` per folder, include line, default ignore patterns |
| `commands` | setup, apply, update, status, commit, push |
| `updates`, `auto_update`, `local_changes`, `local_overrides`, `system_relevance` | update plan and resolvers, background update, relevance filter |
| `attention`, `events` | `machine attention`, local event log |
| `machine` | the `Machine` class combining the modules above |

## Host config and applied copy

**Only source per host:** the host config [`machine/hosts/<hostname>.yml`](../machine/hosts/) — `context`, `device`, features, `ssh_allow_from` and optionally `ansible: false`. `machine setup` writes the selection there directly (also with `--yes`) and offers to commit; commit and push it to share. A host's file can also be changed from another host: the next `machine update` (or the background job) takes it over without a question and prints what changed (for example `+ thunderbird`); `machine update --check` lists it beforehand.  
Applied copy: `~/.local/share/machine/applied-host.yml` (not in git, written only by `machine`; hand edits are undone by the next update; a former `~/.config/machine/profile.yml` is taken over once). It is the state a failed apply reverts to, what the shell reads at start, and the host config of containers. Dotfile groups of the host: `~/.config/mise/config.local.toml` (written by `machine`).

## Layers

| Layer | Responsible for |
| --- | --- |
| `machine/hosts/*.yml` | Desired state (context, device, features) |
| `machine` CLI | Orchestration, UX, secrets, git, calling mise and Ansible |
| mise | Dotfile groups and user-space tools without root (`home/core/.config/mise/conf.d/*.toml`, pinned by `mise.lock`) |
| Ansible | Root work only: apt, `/etc`, system services (Telegraf, sshd-home, laptop and memory roles, …) |
| Inventory | Reachability only — no features |

Work for the login user that needs no root (for example GNOME Shell extensions, also those of the
feature `touch-device`) is done by `machine` and mise, not by Ansible.

## Decision: Ansible stays for root work

Owner decision of 2026-11-08: the split stays — mise and `machine` for the user level, Ansible
for root and system work. The root roles are not migrated to `mise bootstrap`. This replaces the
statement in the archived `adopt-mise` design that replacing "the five root roles" with
`mise bootstrap` is a later change.

Today Ansible has ten local roles (nine feature roles and the model role
`thinkpad_l13_yoga_gen2`) plus the packages play.

`mise bootstrap` is re-evaluated between 2027-05 and 2027-11 against these criteria:

- validation before a file is written (`sshd -t`, `visudo -c`)
- conditions per host and per hardware fact
- debconf
- partial edits of files (as with `lineinfile`)
- a single sudo authentication per run
- a `mise` binary for the Raspberry Pi Zero

## Galaxy vs. local roles

| Need | Decision |
| --- | --- |
| Telegraf | **Local** `roles/monitoring` (InfluxData apt source, Bitwarden output + `machine/*` fragments). Galaxy `dj-wasabi.telegraf` / `boutetnico.telegraf` possible, but heavier and a worse fit. |
| Docker | **apt** `docker.io` / `compose-v2`. Later optionally `geerlingguy.docker` or collection `community.docker`. |
| SSH keys | **Local** `sshd_home` + collection `ansible.posix` (`authorized_key`). |
| Stylus | **Local** (ex helpers-and-automation). |

Collections: `ansible-galaxy collection install -r ansible/requirements.yml`.
