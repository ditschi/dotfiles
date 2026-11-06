# Backlog

New features and improvements that are not yet planned. Each entry becomes an OpenSpec change (`/opsx-propose`) when picked up; discussion and the owner's decision are recorded there. Nothing here is decided.

Improvement entries already have an investigation report in `openspec/investigations/`; section IDs in brackets (for example A3) point to the individual findings and suggestions. Use the report as input for the change.

## Improvements

### Shell layout (planned)

Planned in `openspec/changes/restructure-shell-config`: `.shell/{common,bash,zsh}`, explicit source lists and separately deployed work modules. The assessment and implementation plan are consolidated in that change.

Investigation input: shell-and-prompt A3, A4. The old zinit double-load question is obsolete; the plan preserves deferred completion dependencies.

### Shell startup, plugins and prompt

Measure shell startup before changing anything; reduce overlapping plugins (jump tools, highlighters); guard `fzf-tab` without `fzf`; check the highlighter order; settle skipped prompt profiles and the one-prompt question; fix the `❯` prompt-mark alias bug.

Investigation: shell-and-prompt C1-C7.

### Shell handoff

Find the reason for the Docker and `bash -c` guards, compare the handoff mechanism with alternatives that need no `chsh` (`override_shell`, `.profile`), add a `chsh` wrapper for work hosts, add a fresh-install test with a temporary zinit home.

Investigation: shell-and-prompt A1, A2, A5, B1; shell-handoff-zsh-default.

### Git config cleanup

Review the credential helper layout and the `store` fallback (keyring helper as a safer option), `user.useConfigOnly`, and suspected legacy keys.

Investigation: baseline-git-config 1-4.

### Env and secrets

Review load order, flexible env file locations, permission fixing in `machine env pull`, `git-credential-env` paths per host type, and an optional Bitwarden source in `get-password`.

Investigation: env-and-update A1-A5.

### Update flow

Review the update timer, when Ansible runs (hint-only variant), the restore after a failed apply (likely bug in `cmd_update`), the layout migration offer, the reload hint after an update, syncing local changes, automatic rollout with rollback, and remote updates over SSH.

Investigation: env-and-update B1-B8; provisioning 6.

### Kerberos and LDAP

Review the feature name, the callers of the helpers, the refresher in Ansible, the password fallback order across contexts, and LDAP region selection.

Investigation: kerberos-and-quality A1-A5.

### Profiles and work/private separation

Review the default profile order, container precedence, a profile-to-groups table, `WORK_SETUP` in dev containers, work detection signals, profile versus feature, and sensitive work data in the shared repository.

Investigation: architecture-and-profiles B1-B7; repo-sensitivity.

### Repo hygiene and provisioning

Keep Ansible but thin the roles; find a route for work machines without root; run `node_tools` only when needed; make OpenSpec an explicit feature; record the purpose of `etckeeper`; a bootstrap entry script; a Python version CI matrix; remove `install.py` and the migration code; trim `machine` subcommands; remove the dead pre-commit hook; define the checks required before commit.

Investigation: provisioning 1-5; architecture-and-profiles A1-A6; kerberos-and-quality B1-B3.

### SSH agent forwarding for trusted hosts

Requested 2026-11-03 from the homelab SOPS/GitOps plan (homelab repo `docs/compose-gitops.md`): servers get a read-only GitHub deploy key, and commits made on a server are pushed with the personal key through agent forwarding, so no server holds a key that can write to GitHub.

To settle:
- Where `ForwardAgent yes` is set. The `ssh-client-config` spec forbids it under `Host *` and leaves it to `config.local`; decide whether the Bitwarden host list (`ssh/<class>/config`) may mark trusted hosts (homeserver, netmaster) instead. Oracle (public) stays opt-in with `ssh -A`.
- Which agent holds the key. Keys have no passphrase and `AddKeysToAgent` is not set, so a running agent may hold nothing to forward; check desktop (GNOME keyring / ssh-agent) and headless hosts.
- Confirm-on-use (`ssh-add -c`) for forwarded keys, and whether it works without a GUI askpass.
- Whether the per-host GitHub key that the SSH key flow registers on servers should be dropped once deploy keys and forwarding exist (a server key with write access to every repo is the risk this replaces).

### Bitwarden CLI: evaluate `rbw` as a full replacement

Only switch if `rbw` can replace `bw` completely; two tools would mean maintaining the logic twice. Until then the CLI keeps `bw` only.

Spike (2026-10-22, `rbw` 1.15.0 against Vaultwarden 1.37.4): login, sync, reading secure notes and hidden fields, prefix search and a silent unlock through a scripted pinentry work. `rbw add` and `rbw edit` fail with HTTP 422 because Vaultwarden 1.37 requires `encryptedFor`; tracked upstream as `doy/rbw#385` (open, a patch and a fork exist, no release yet).

Still open after that fix: `add` and `edit` only handle Login items, not secure notes with custom fields, so the SSH items would need a format migration; a silent unlock needs the master password in the keyring, which contradicts the `secret-tools` spec (owner decision).

Revisit when `doy/rbw#385` is fixed and released.

### Take over all host setup from the homelab repo

Owner decision 2026-11-06: the homelab repo removes its Ansible completely (change `retire-homelab-ansible` there; it replaces `shrink-homelab-ansible`). It was never applied. Everything that must stay true on a host moves here, because the dotfiles run on every host and update on login. One-off homelab actions (K3s install or join, restore from the NAS, the NAS NFS mount and the Oracle repo pull on homeserver, the Oracle restic script) stay in the homelab repo as scripts or `homelab` CLI commands. Neither repo calls the other; the dotfiles run first on a new or rebuilt host.

Needed here:
- `sshd_home`: disable SSH password and keyboard-interactive login (the homelab `access` role was meant to do this but was never applied).
- oracle (`machine/hosts/privatecloud.yml`): enable `monitoring` and `sshd-home`.
- inotify limits on every server that runs containers (Docker hosts and the K3s nodes homeserver and netmaster, where they are set by hand today in `/etc/sysctl.d/60-k3s-inotify.conf`): `fs.inotify.max_user_instances=1024`, `fs.inotify.max_user_watches=524288`. Only raise, never lower: since Linux 5.11 the kernel default for `max_user_watches` scales with RAM (about 1 % of RAM, up to 1048576), so on a large host a fixed 524288 would cut the default and hurt IDE and file watchers (for example a remote work VM with VS Code). The limits are caps, not reservations; a watch costs about 1 KB of kernel memory only while it exists.
- CI deploy key on the compose hosts (oracle, contabo, later homeserver and netmaster) through `machine/ssh_keys` and `ssh_allow_from`; on contabo it is in `authorized_keys` by hand today. Note: `sshd_home` adds keys with `exclusive: false`, so keys added by hand stay until removed.
- Feature `homelab-node` (was planned as a homelab Ansible role in homelab `docs/compose-gitops.md`): sops as a pinned release binary with checksum, the host age key from Bitwarden (`homelab-age-<host>`, hidden field `private_key`) in `~/.config/sops/age/keys.txt` (mode 600), a read-only GitHub deploy key, the clone at `/opt/homelab`, and the `homelab` CLI on `PATH`. contabo has sops and its age key by hand today.
- `machine env pull` writes the personal age key (`homelab-age-key`) to `~/.config/sops/age/keys.txt` on laptops.
- Clean-up: remove the stub `ansible/homelab.yml`, the `homelab` entry in `PLAYBOOKS` (`machine_cli/core.py`), the special case in `machine_cli/tools.py`, its lint entry in `.github/workflows/verify.yml` and `noxfile.py`, and the notes in `Readme.md`, `ansible/README.md` and `machine/hosts/README.md`.

## New Features

### Automatic VPN on work machines outside the corporate network

Idea from the owner: on work machines, detect which network the machine is on. When it is not the corporate network (not onsite, for example at home or on a travel or hotspot connection), start the VPN automatically.

Wanted scope:
- Network types: LAN, Wi-Fi and USB network (for example USB tethering).
- Profiles: work-machine only.

Open questions (to ask when this is picked up):
- How to recognise the corporate network reliably (DNS suffix, reachable internal host, gateway, SSID).
- Which VPN client and how it is started without root, since work machines may not allow Ansible to become root.
- What triggers the check (network change event, shell start, timer) and how to avoid flapping between networks.
- Whether the user can pause or override the automatic start.

### zellij: theme and options

Idea from the owner: adapt zellij's look with built-in settings. Only `copy_command` is set today. A theme and plain options do not touch the default-key-bindings requirement of the `terminal-multiplexer` spec.

Links:
- https://rodbv.github.io/zellij-theme-gallery/themes/gruber-darker.html
- https://rodbv.github.io/zellij-theme-gallery/themes/ao.html
- https://rodbv.github.io/zellij-theme-gallery/themes/solarized-light.html

Notes from a first look (2026-10-25, zellij 0.45.1):
- The three themes are built into zellij; no theme files or `theme_dir` are needed.
- `theme_dark` and `theme_light` switch automatically when the terminal reports its colour palette (for example `gruber-darker` or `ao` dark, `solarized-light` light). Without a report zellij stays on the dark theme. The desktop is set to `prefer-dark`.
- `zellij setup --check` does not validate theme names; a typo only shows at start.
- Built-in options worth a look: `default_layout "compact"`, `show_release_notes false`, `show_startup_tips false`, `mouse_hover_tips false`, `pane_frames false`, `scroll_buffer_size`.

Open questions (to ask when this is picked up):
- Which dark theme: `gruber-darker` or `ao`?
- Do Ptyxis and GNOME Terminal report their colour palette, so that automatic dark/light switching works?
- Which of the built-in options the owner wants.

### zellij: plugins (source, pinning, autolock vs. spec)

Idea from the owner: add a few zellij plugins.

Link: https://github.com/zellij-org/awesome-zellij

Candidates from the list (first look, 2026-10-25):
- `zellij-autolock`: locks zellij automatically for programs such as fzf, nano or Claude Code, which would remove the Ctrl+G detour.
- `zjstatus`: configurable status bar.
- `zellij-forgot`: overview of the key bindings.
- `zellaude` or `zellij-attention`: Claude Code activity on tabs.

Open questions (to ask when this is picked up):
- Source and pinning: plugins are WASM files from GitHub releases that mise does not manage. Keep them in the repository, or download them with a pinned version and checksum? How are updates picked up?
- `zellij-autolock` changes when keys reach zellij; is that acceptable under the default-key-bindings requirement of the `terminal-multiplexer` spec, or does it need a spec change?
- Which plugins add or change key bindings, and whether that is wanted at all.
