# Backlog

New features and improvements that are not yet planned. Each entry becomes an OpenSpec change (`/opsx-propose`) when picked up; discussion and the owner's decision are recorded there. Nothing here is decided.

Improvement entries already have an investigation report in `openspec/investigations/`; section IDs in brackets (for example A3) point to the individual findings and suggestions. Use the report as input for the change.

## Improvements

### Restructure `~/.zsh` by use

Split the flat `home/core/.zsh/config/` into zsh-only modules, modules shared with bash (must stay bash-compatible) and a work folder, so that loading and the work-profile exclusion become simpler. Also check whether `07_machine.zsh` is sourced twice.

Investigation: shell-and-prompt A3, A4. Draft change: `openspec/changes/investigate-shell-layout` (classification of the modules).

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

### Bitwarden CLI: evaluate `rbw` as a full replacement

Only switch if `rbw` can replace `bw` completely; two tools would mean maintaining the logic twice. Until then the CLI keeps `bw` only.

Spike (2026-10-22, `rbw` 1.15.0 against Vaultwarden 1.37.4): login, sync, reading secure notes and hidden fields, prefix search and a silent unlock through a scripted pinentry work. `rbw add` and `rbw edit` fail with HTTP 422 because Vaultwarden 1.37 requires `encryptedFor`; tracked upstream as `doy/rbw#385` (open, a patch and a fork exist, no release yet).

Still open after that fix: `add` and `edit` only handle Login items, not secure notes with custom fields, so the SSH items would need a format migration; a silent unlock needs the master password in the keyring, which contradicts the `secret-tools` spec (owner decision).

Revisit when `doy/rbw#385` is fixed and released.

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
