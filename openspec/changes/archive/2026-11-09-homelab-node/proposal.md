# Proposal: homelab-node

## Why

The homelab repository (github.com/ditschi/homelab) moves its Docker Compose hosts from rsync copies to stacks that run straight from a git clone on each host, deployed by CI with `ssh <host> homelab deploy <sha>`. Each Compose host therefore needs the same base: a clone that can fetch without the personal key, sops with the host's own age key, and the `homelab` CLI on the PATH of non-interactive SSH sessions. The dotfiles already set up these hosts and hold the Bitwarden access, so they provide this base as a feature instead of a manual setup per host.

The contract comes from the homelab repository: change `compose-repo-clones`, the compose-hosts requirement "Repository clone on every Compose host" and `docs/compose-gitops.md` (sections "Keys" and "Host layout").

## What Changes

- New feature `homelab-node` in the feature table: optional on private servers, excluded on desktops, for work and in containers. It selects no dotfile group.
- New optional host config block `homelab:` with `host` (the homelab host key, used for the Bitwarden item name), `user` (deploy user), `clone` (checkout path, default `/opt/homelab`) and `ci_restrict` (restrict an existing CI key entry). Every rewrite of the host config keeps it, like `disk_space`.
- A fresh VM that only has `root` is finished with the dotfiles bootstrap alone. When `machine` runs as root, the deploy user defaults to `ditschi`. The role creates it when missing (password locked, key login only, no sudo, `docker` group). It gets the keys that `sshd-home` grants for `ssh_allow_from` and the homelab CI key from `machine/ssh_keys/homelab-ci.pub`. A newly added CI key is limited to `homelab deploy <sha>` by a forced command. An existing CI key entry keeps its options until the host config sets `homelab.ci_restrict: true`, so the current rsync deploy keeps working until CI switches. On contabo, where only `root` is reachable today, `ssh ditschi@contabo` then works with the owner's keys.
- New Ansible role `homelab_node`, applied when the host has the feature. It runs idempotently and makes sure that:
  1. a clone of the homelab repository on branch `main` exists at `/opt/homelab`, owned by the deploy user. A configured path other than `/opt/homelab` is an existing checkout (homeserver: `/mnt/data-internal/homelab`); it is used as it is, with no clone and no deploy key;
  2. a per-host ed25519 deploy key exists (generated on the host, mode 600) and is used only by this clone through `core.sshCommand`. The public key is printed so the owner can add it as a read-only deploy key in GitHub. Pushing from the host keeps working only with a forwarded personal agent key;
  3. sops 3.13.3 is installed from the GitHub release with its sha256 checked, on the deploy user's PATH;
  4. the host age key from the Bitwarden item `homelab-age-<host>` (hidden field `private_key`) is in `~/.config/sops/age/keys.txt` of the deploy user, mode 600. The personal age key is never written on a server;
  5. `/usr/local/bin/homelab` and `/usr/local/bin/hl` are symlinks to `<clone>/scripts/homelab.py`, git, python3 and PyYAML are installed, the Docker Compose plugin is checked, and the deploy user is in the `docker` group.
- `machine setup`, `machine apply` and the apply step of `machine update` read `homelab-age-<host>` before Ansible on hosts with the feature and hand it only to Ansible, the same way as the Telegraf item.
- A missing Bitwarden item, a deploy key that GitHub does not accept yet, or a missing Docker or Compose does not stop the run. `machine attention` names each one, showing the public key until fetch works. The clone follows on the next run.
- The role never touches running containers or anything under the host's data root (`/mnt/volume/containers` on oracle, `/opt/containers` on contabo). It does not reboot, prune or restart containers (contabo runs GuardedSleep).

## Capabilities

### New Capabilities
- `homelab-node`: the base for a homelab Compose host: clone, deploy key, sops, host age key, `homelab` CLI and what is reported when parts are missing.

### Modified Capabilities
- `feature-selection`: the feature `homelab-node` and its values per context and device.
- `machine-profiles`: the optional host config block `homelab`, kept on every rewrite.
- `secret-tools`: the item `homelab-age-<host>` is read before Ansible, only reaches Ansible, and a missing item does not block the run.

Profiles: private servers only. Today these are `privatecloud` (oracle, deploy user `ubuntu`), `contabo` (deploy user `ditschi`, `machine` runs as root) and `homeserver` (existing checkout); `netmaster` later; and every new VM bootstrapped as root.

## Impact

- `ansible/group_vars/all/features.yml`, `ansible/workstation.yml` (new play), new `ansible/roles/homelab_node/`.
- `machine_cli`: host config parsing and writing (`profile.py`), Bitwarden handover before Ansible (`bw_client.py`, `tools.py`), attention items.
- `machine/ssh_keys/homelab-ci.pub` (public half of the homelab secret `COMPOSE_SSH_KEY`, supplied by the owner).
- `machine/hosts/privatecloud.yml`, `contabo.yml` and `homeserver.yml` get the feature and the `homelab:` block when the owner enables it.
- Docs: `docs/features.md`, `docs/secrets.md`, `docs/host-config.md`, role README.
- Tests: unit tests for the feature table, host config key, Bitwarden handover and the role (pattern of `test_monitoring_role.py`).
- External: the owner adds one deploy key per host in GitHub, and creates the Bitwarden items `homelab-age-<host>` where they are still missing.

Where: worktree `$(machine repo)/.worktrees/homelab-node`. The change adds an Ansible role and changes `machine_cli`, which affect the host's tools at the next `machine` run.

## Assumptions

- The homelab CI workflow connects as `ditschi` to contabo, homeserver and netmaster and as `ubuntu` to oracle (`.github/workflows/compose-deploy.yml`, checked 2026-11-09), so these are the deploy users.
- The homelab host key equals `hostname -s` unless `homelab.host` is set. oracle needs `host: oracle`, because its hostname is `privatecloud`.
- The Bitwarden items `homelab-age-oracle`, `homelab-age-homeserver` and `homelab-age-contabo` exist as the homelab docs describe (secure note, hidden field `private_key`, text field `public_key`).
- The homelab change `compose-repo-clones` is not in the homelab repository yet (checked 2026-11-09). The behaviour here follows the owner's request and `docs/compose-gitops.md` on branch `compose-gitops`.
