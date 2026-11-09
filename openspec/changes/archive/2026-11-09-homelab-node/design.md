# Design: homelab-node

## Context

See proposal.md - Why. State of the three hosts, checked read-only on 2026-11-09:

| Host (hostname) | `machine` runs as | Deploy user | Checkout | sops today | age key file |
|---|---|---|---|---|---|
| oracle (`privatecloud`) | `ubuntu` | `ubuntu` | none | `/usr/local/bin/sops` | not checked |
| contabo (`contabo`) | root (`/root/dotfiles`) | `ditschi` (key login only, no password known) | none | `/usr/local/bin/sops` | not checked |
| homeserver (`homeserver`) | `ditschi` | `ditschi` | `/mnt/data-internal/homelab` (`main`, uses the personal key) | `~/.local/bin/sops` 3.13.3, hidden by a mise shim without a version | present, mode 600 |

- Non-interactive SSH sessions on oracle and homeserver have `~/.local/share/mise/shims` first on PATH. On homeserver `sops` therefore fails in exactly the session CI uses.
- `scripts/homelab.py` already exists in the homelab repo (K3s host commands). It and `scripts/lib.py` call `sops` from PATH and rely on sops' default key path `~/.config/sops/age/keys.txt`. The homelab repo has no code that fetches the age key from Bitwarden; its `bw` use covers only K3s tokens.
- `machine` already reads one Bitwarden item before Ansible: `influxdb-telegraf-write`. It goes to Ansible as an extra-vars file that only the user can read and that is removed afterwards (`tools.py`, `bw_client.influx_credentials`).
- The host config already has one optional block that every rewrite keeps: `disk_space`.
- Ansible runs as root locally (`machine_runs_as_root`). Tasks for the login user use `become_user`; this role uses the deploy user instead.

## Goals / Non-Goals

**Goals:**
- One role, the same on every Compose host. Host differences live only in the `homelab:` block of the host config.
- Every step is idempotent and can be repeated; a step that cannot finish yet (missing key in GitHub or Bitwarden) leaves the run successful and shows up in `machine attention`.

**Non-Goals:**
- Starting stacks, `homelab up` or any Compose command. That is the homelab repo's job.
- Passwords or sudo rules for the deploy user.
- Agent forwarding settings in the SSH client config (`ForwardAgent` per host). That belongs to the `ssh-client-config` capability and is not part of this change.
- Removing the personal GitHub key that the dotfiles place on servers today.
- Converting homeserver's checkout to a deploy key.

## Decisions

### Host config block instead of host-derived rules
`homelab: {host, user, clone, ci_restrict}` with defaults `hostname -s`, the login user (`ditschi` when `machine` runs as root) and `/opt/homelab`. The checked hosts show that no single rule fits: oracle's hostname is `privatecloud` while its homelab name is `oracle`, `machine` runs as root on contabo, and homeserver keeps another path. The block follows the `disk_space` pattern, so profile parsing, writing and takeover need one more preserved key and no new mechanism.

### Bootstrap as root is enough (owner decision, 2026-11-09)
A new VM often has only `root`. The owner wants to bootstrap the dotfiles there and be done. On contabo the owner can log in only as root, while CI connects as `ditschi`. So when `machine` runs as root, the deploy user defaults to `ditschi`, and the role creates it when missing: home directory, the login user's shell, locked password, no sudo (owner decision). Administration stays with root. The deploy user only needs key login and the `docker` group. Existing users keep their password, shell and groups.

### Logins for owner and CI from the repository (owner decision, 2026-11-09)
The deploy user's `authorized_keys` gets the same `machine/ssh_keys/<host>.pub` keys that `sshd-home` grants the login user for `ssh_allow_from`. The owner can then `ssh ditschi@<host>`, and `ssh -A` for pushing. It also gets the public half of the homelab CI secret `COMPOSE_SSH_KEY` from `machine/ssh_keys/homelab-ci.pub`, so CI reaches a new host without a manual step. Entries are only added (`ansible.posix.authorized_key`, `exclusive: false`), so contabo's hand-added CI key stays.

### Existing checkout means "hands off its git config"
A `clone` other than `/opt/homelab` marks a checkout the owner manages. The role links the CLI into it and sets up sops and the age key, but never clones, never creates a deploy key and never changes its git config. This covers homeserver without a second feature.

### Deploy key bound to the clone through `core.sshCommand`
The clone's `.git/config` gets:

```
core.sshCommand = ssh -i ~/.ssh/homelab_deploy_ed25519 -o UserKnownHostsFile=/etc/ssh/homelab_github_known_hosts -o StrictHostKeyChecking=yes
```

`IdentitiesOnly` is deliberately not set. ssh offers agent keys first, so with `ssh -A` GitHub authenticates the owner's personal key and push works. Without an agent, only the deploy key is offered and works for fetch only, because it is read-only in GitHub. The key appears only in this clone's config, not in `~/.ssh/config`, so it is never offered to other repositories. GitHub's published host keys are shipped with the role and installed to `/etc/ssh/homelab_github_known_hosts`, so the first non-interactive fetch from CI does not depend on a prompt or on `accept-new`.

Considered: a `Host github-homelab` alias in `~/.ssh/config`. Rejected because it changes the user's SSH client config, which the dotfiles generate, and the remote URL would differ from the one the homelab docs use.

### Acceptance check without the agent
The role tests the key with `git ls-remote` with the deploy key alone (`-F /dev/null`, `IdentitiesOnly=yes`, `IdentityAgent=none`). Neither an agent forwarded during `machine apply` nor an `IdentityFile` for github.com in the user's SSH config can make an unaccepted key look accepted. A failed clone (for example a non-empty `/opt/homelab` without git) is recorded and reported; it does not fail the run. When the key is accepted and `/opt/homelab` has no repository, the role clones `main`. Otherwise it prints the public key and records the state.

### Remote runs resolve the target host
`machine apply --limit <host>` resolves the `homelab` block of that host's config with `<host>` as the default host name and reads `homelab-age-<host>`. It sends no user unless `homelab.user` is set; the role then uses the connecting user, or `ditschi` for root. Only the Bitwarden item whose name matches exactly is used, because `bw get item` also matches by search.

### Status file for `machine attention`
The role writes its findings at each run to `/var/lib/machine/homelab-node.json` (mode 644, no secrets): deploy user problem, clone state, public key when not accepted, key file state (missing, written, differs), the sops path and version from the deploy user's non-interactive environment, and Docker/Compose availability. `machine attention` reads only this file. It needs neither root nor network, and the hosts where `machine` runs as another user than the deploy user work the same. The state is as fresh as the last apply. Every listed problem is fixed by an action followed by `machine apply`, which refreshes it.

### Non-interactive SSH environment emulated
sshd runs `$SHELL -c <command>`. The role runs the deploy user's login shell the same way, with a clean environment (`HOME`, `USER`, `LOGNAME`, `SHELL`, the PATH from `/etc/environment`, and `SSH_CLIENT` set so that bash reads `~/.bashrc` as it does under sshd), and records `command -v sops` and `sops --version`. This finds the homeserver shim case without an SSH connection to localhost.

### sops in `/usr/local/bin`, pinned by checksum
The role downloads `sops-v3.13.3.linux.<amd64|arm64>`, checks it against the sha256 pinned in the role defaults (taken from the release's checksums file), and installs it to `/usr/local/bin/sops` with mode 755. `/usr/local/bin` is on every user's default PATH and matches what oracle and contabo already have. Considered: mise in the dotfile groups. Rejected because mise shims depend on the user's activation, which is exactly what fails on homeserver, and because root-owned CI paths should not depend on a user tool manager.

### Age key handed over like the Telegraf item
`machine` reads `homelab-age-<host>` before Ansible on hosts with the feature and adds `homelab_age_private_key` to the private extra-vars file it already uses for Influx. The role writes it with `no_log: true`. When the item or field is missing, the variable is absent and the role only checks the existing file. The item name is built only from `homelab.host`, and `key` is refused, so the personal item `homelab-age-key` can never be selected.

### CI key limited to `homelab deploy` (owner decision, 2026-11-09)
The deploy user is in the `docker` group, which is root-equivalent, so an unrestricted CI key would be root on the host. CI needs only `homelab deploy <sha>`. The role installs `/usr/local/bin/homelab-ci` and adds the CI key with `restrict,command="/usr/local/bin/homelab-ci"`. The wrapper reads `SSH_ORIGINAL_COMMAND`, accepts only `homelab deploy <hex sha, 7-40 characters>` and runs `/usr/local/bin/homelab deploy <sha>` without a shell. Anything else exits non-zero. A leaked CI key can then only deploy commits that exist in the repository. Considered: `restrict` only (any command, so still root through `docker`) and unrestricted (as on contabo today); both rejected for that reason.

### Existing CI key entries stay until CI switches (owner decision, 2026-11-09)
The current CI deploy (`scripts/compose_deploy.py`) runs `mkdir`, `rsync` and arbitrary commands over SSH. It switches to `homelab deploy` only in rollout step 8 of the homelab plan. So the role adds the restricted entry only where the CI key is missing (new hosts). An existing entry (contabo, oracle) keeps its options until the host config sets `homelab.ci_restrict: true`, after the switch. Considered: a wrapper with a pass-through legacy mode (the restriction is not real until it is removed), and restricting at once (breaks the rsync deploy).

### Existing age key file is kept (owner decision, 2026-11-09)
The key file is written only when it is missing or holds no `AGE-SECRET-KEY-` line. A file with another key is kept and reported. A working, hand-placed key (homeserver) is never overwritten by mistake.

### Other sops installations are reported, not removed (owner decision, 2026-11-09)
The role installs `/usr/local/bin/sops` and only reports, in `machine attention`, when another `sops` wins in the deploy user's non-interactive SSH environment (homeserver's mise shim). It does not uninstall tools the dotfiles did not install.

### Docker group, no engine changes
The role adds the deploy user to `docker` (`append: true`) when the group exists and changes nothing else about Docker. This keeps the `docker` feature's rule that existing providers are preserved. A new group membership applies to new SSH sessions only, which is enough for CI.

### Safety boundary
The role has no task that calls `docker` other than `docker compose version`, no `reboot`, no `prune`, and no path under a data root. A unit test checks the role files for forbidden commands (`docker (compose )?(up|down|restart|rm|stop|start|prune)`, `reboot`, `systemctl restart docker`) and for the data roots.

## Risks / Trade-offs

- [The personal GitHub key that the dotfiles place in `~/.ssh` of the deploy user (oracle has `id_ed25519`) is offered after the agent keys] → With `-i` set, ssh does not add the default identity files unless `~/.ssh/config` names them for github.com. Implementation checks the generated config. If it names them, push without an agent keeps working until that key leaves the servers; this is reported, not fixed here.
- [Status file goes stale when Ansible is skipped] → `machine attention` shows the time of the last run in the item text.
- [GitHub rotates its host keys] → The fetch fails loudly with a host key error. The role's known-hosts file is updated in the repo, and the next `machine update` installs it.
- [Group membership needs a new session] → Documented. CI opens a new session per deploy.
- [`docker` group membership is root-equivalent, so the CI key and the owner's keys can become root through the deploy user] → The owner's keys already log in as root on these hosts, so this adds no access for them. The CI key is limited to `homelab deploy`, except existing entries until `ci_restrict` is set.
- [`ci_restrict` forgotten after the CI switch] → `machine attention` reports an unrestricted CI key entry once the host's clone exists and `ci_restrict` is not set. The homelab rollout step 8 names setting it.
- [`homelab-ci.pub` missing from the repository] → The run reports it; the owner adds the key file.

## Migration Plan

1. Merge. No host changes until the feature is selected. The owner commits `machine/ssh_keys/homelab-ci.pub`.
2. contabo first (staging): add the feature, `machine apply` as root (`ditschi` exists and gets the owner's keys). Add the printed deploy key in GitHub, `machine apply` again. Check `ssh ditschi@contabo homelab --help`, and that GuardedSleep containers kept their start times.
3. oracle: `homelab: {host: oracle}`, feature on, same steps.
4. homeserver: `homelab: {clone: /mnt/data-internal/homelab}`, feature on. Remove the stale mise sops shim by hand (`mise uninstall sops`) once attention reports it.
5. After CI uses `homelab deploy` (homelab rollout step 8): set `homelab.ci_restrict: true` on contabo and oracle, `machine apply`.
6. New VM: bootstrap the dotfiles as root with `homelab-node` in its host config, add the printed deploy key in GitHub, `machine apply` again. Done.
7. Rollback: remove the feature. Nothing is removed (see spec). Delete `/opt/homelab`, the deploy key, the links and the user by hand if wanted.
