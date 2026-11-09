# Spec Delta

## Purpose

Prepares a homelab Docker Compose host so that CI and the owner can run stacks straight from a git clone of the homelab repository: clone, read-only deploy key, sops with the host age key and the `homelab` CLI, without touching running containers or their data.

## ADDED Requirements

### Requirement: Deploy user
The role SHALL act for one deploy user: `homelab.user` from the host config; otherwise the login user of `machine`, or `ditschi` when `machine` runs as root. Root SHALL NOT be a deploy user; a `homelab.user: root` SHALL make the role change nothing and `machine attention` SHALL say why.

#### Scenario: oracle
- **WHEN** `machine apply` runs as `ubuntu` on a host with `homelab-node` and no `homelab.user`
- **THEN** `ubuntu` is the deploy user

#### Scenario: Fresh VM bootstrapped as root
- **WHEN** `machine setup` runs as root on a new host with `homelab-node` and no `homelab` block
- **THEN** `ditschi` is the deploy user

#### Scenario: Root configured
- **WHEN** the host config sets `homelab.user: root`
- **THEN** nothing is set up and `machine attention` names the invalid user

### Requirement: Deploy user created when missing
When the deploy user does not exist, the role SHALL create it with a home directory, the login shell of the login user, and a locked password, without sudo rights. Existing users SHALL keep their password, shell and groups.

#### Scenario: Fresh VM
- **WHEN** `machine setup` runs as root on a host without `ditschi`
- **THEN** `ditschi` exists with a locked password and a home directory

### Requirement: Login for owner and CI
The role SHALL add to the deploy user's `authorized_keys` the keys that `sshd-home` grants for the host's `ssh_allow_from`, and the homelab CI key from `machine/ssh_keys/homelab-ci.pub`. Existing entries SHALL be kept. A missing key file SHALL be reported, not fail the run.

#### Scenario: contabo after apply
- **WHEN** `machine apply` has run as root on contabo, whose `ssh_allow_from` lists the owner's laptop
- **THEN** the owner logs in as `ditschi` with the laptop key, and the CI key already present is still accepted

#### Scenario: New VM reachable by CI
- **WHEN** a new host was bootstrapped as root with `homelab-node`
- **THEN** CI can connect as `ditschi` with `COMPOSE_SSH_KEY` without a manual step

### Requirement: CI key limited to deploy
A CI key entry that the role adds SHALL carry `restrict` and a forced command that runs only `homelab deploy <sha>` (a hexadecimal commit id of 7 to 40 characters) and rejects any other command with a non-zero exit. An existing CI key entry SHALL keep its options unless the host config sets `homelab.ci_restrict: true`; then the role SHALL replace its options with the same restriction.

#### Scenario: Deploy from CI on a new host
- **WHEN** CI runs `ssh ditschi@<host> homelab deploy 0803d4e`
- **THEN** `homelab deploy 0803d4e` runs

#### Scenario: Other command with the CI key
- **WHEN** a client with the CI key runs `ssh ditschi@<host> 'docker ps'` on a host where the key was added by the role
- **THEN** the command is rejected and nothing runs

#### Scenario: contabo during the rsync phase
- **WHEN** contabo's existing CI key entry has no options and `homelab.ci_restrict` is not set
- **THEN** the entry is unchanged and the rsync deploy keeps working

#### Scenario: After CI switched
- **WHEN** the host config sets `homelab.ci_restrict: true` and `machine apply` runs
- **THEN** the existing CI key entry gets the forced command

### Requirement: Repository clone
The clone path SHALL be `homelab.clone`, default `/opt/homelab`. When the path is `/opt/homelab` and holds no git repository, the role SHALL clone `git@github.com:ditschi/homelab.git` on branch `main` there, owned by the deploy user. An existing clone SHALL NOT be fetched, reset or switched to another branch.

#### Scenario: First run with an accepted deploy key
- **WHEN** `/opt/homelab` does not exist and GitHub accepts the host's deploy key
- **THEN** `/opt/homelab` is a clone on branch `main` owned by the deploy user

#### Scenario: Clone with local changes
- **WHEN** `/opt/homelab` is a clone with uncommitted changes on another branch
- **THEN** a run leaves its branch, working tree and history unchanged

### Requirement: Existing checkout elsewhere
When `homelab.clone` names a path other than `/opt/homelab`, the role SHALL use that checkout as it is: no clone, no deploy key and no change to its git config. When the path holds no git repository, `machine attention` SHALL name it.

#### Scenario: homeserver
- **WHEN** the host config sets `homelab.clone: /mnt/data-internal/homelab`
- **THEN** the CLI links point into that checkout, sops and the age key are set up, and no deploy key is created

### Requirement: Read-only deploy key
For a clone at `/opt/homelab`, the role SHALL create an ed25519 key `~/.ssh/homelab_deploy_ed25519` for the deploy user once (mode 600, comment naming the host), and SHALL set the clone's `core.sshCommand` to use it. An existing key SHALL be kept. The key SHALL NOT be used for any other repository or host.

#### Scenario: Second run
- **WHEN** the key already exists
- **THEN** it is not replaced and its public key stays the same

#### Scenario: Other git repositories
- **WHEN** the deploy user fetches another repository from GitHub
- **THEN** the deploy key is not offered

### Requirement: Push only with a forwarded agent key
Fetch from the clone SHALL work with the deploy key alone. When the deploy user connects with a forwarded agent that holds the owner's personal key, push from the clone SHALL use that key. The role SHALL NOT place a key that can write to GitHub on the host.

#### Scenario: Fetch from CI
- **WHEN** `ssh <host> homelab deploy <sha>` fetches without agent forwarding
- **THEN** the fetch authenticates with the deploy key

#### Scenario: Push with ssh -A
- **WHEN** the owner connects with `ssh -A` and runs `git push` in the clone
- **THEN** the push authenticates with the forwarded personal key

### Requirement: Deploy key shown until GitHub accepts it
While GitHub does not accept the deploy key, `machine apply` SHALL print its public key with the hint to add it under GitHub → Deploy keys with write access off. `machine attention` SHALL report it until it is accepted, and the clone SHALL follow on the next run.

#### Scenario: Key not yet added
- **WHEN** the deploy key was just created and the owner has not added it in GitHub
- **THEN** the run finishes, prints the public key, and `machine attention` shows it with the hint

#### Scenario: Key added
- **WHEN** the owner has added the key and runs `machine apply` again
- **THEN** the clone is created and the attention item is gone

### Requirement: Pinned sops
The role SHALL install sops 3.13.3 for the host's architecture from the GitHub release to `/usr/local/bin/sops`, after checking the binary against the release's sha256 checksum. A binary with another checksum SHALL NOT be installed. An installed sops 3.13.3 SHALL be left alone.

#### Scenario: Checksum mismatch
- **WHEN** the downloaded binary does not match the pinned sha256
- **THEN** nothing is installed and the run reports the mismatch

### Requirement: sops reachable for the deploy user
`machine attention` SHALL report when `sops --version` in a non-interactive SSH session of the deploy user is not 3.13.3, and name the path that runs instead. The role SHALL NOT remove other sops installations.

#### Scenario: Stale mise shim
- **WHEN** a mise shim without a version comes before `/usr/local/bin` on the deploy user's PATH
- **THEN** `machine attention` names the shim path as the one that wins

### Requirement: Host age key
When the item `homelab-age-<host>` was read, the role SHALL write its `private_key` to `~/.config/sops/age/keys.txt` of the deploy user (directory 700, file 600), only when that file is missing or holds no age secret key. A file that holds another key SHALL be kept and reported in `machine attention`.

#### Scenario: Fresh host
- **WHEN** the deploy user has no key file and the item was read
- **THEN** the key file holds the host's age key with mode 600

#### Scenario: Hand-placed key differs
- **WHEN** the key file holds an age key other than the one in Bitwarden
- **THEN** the file is unchanged and `machine attention` reports the difference

### Requirement: No personal age key on servers
The role SHALL write only the item `homelab-age-<host>`. It SHALL never read or write the personal item `homelab-age-key`, and SHALL refuse a `homelab.host` of `key`.

#### Scenario: Wrong host name
- **WHEN** the host config sets `homelab.host: key`
- **THEN** no age key is written and the run reports the invalid name

### Requirement: homelab CLI for non-interactive sessions
The role SHALL make `/usr/local/bin/homelab` and `/usr/local/bin/hl` symlinks to `<clone>/scripts/homelab.py`, and install git, python3 and PyYAML from the system packages, so that `ssh <host> homelab …` works without a login shell.

#### Scenario: CI deploy
- **WHEN** CI runs `ssh <host> homelab deploy <sha>`
- **THEN** `/usr/local/bin/homelab` resolves to the clone's `scripts/homelab.py`

#### Scenario: Clone not there yet
- **WHEN** the clone does not exist yet because the deploy key is not accepted
- **THEN** the links are created anyway and work once the clone exists

### Requirement: Docker access for the deploy user
The role SHALL add the deploy user to the `docker` group. It SHALL NOT install or change the Docker engine. `machine attention` SHALL report a missing `docker` CLI or `docker compose` plugin.

#### Scenario: Compose plugin missing
- **WHEN** `docker compose version` fails on the host
- **THEN** the run continues and `machine attention` names the missing Compose plugin

### Requirement: Running services stay untouched
The role SHALL NOT start, stop, restart, recreate or prune containers, images, volumes or networks, SHALL NOT reboot the host, and SHALL NOT read or write below the host's data root.

#### Scenario: contabo with GuardedSleep
- **WHEN** `machine apply` runs on contabo with `homelab-node`
- **THEN** every container keeps its start time and `/opt/containers` is unchanged

### Requirement: Deselecting removes nothing
Removing `homelab-node` from a host SHALL leave the clone, the keys, sops and the links in place.

#### Scenario: Feature removed
- **WHEN** the feature is removed and `machine apply` runs
- **THEN** `/opt/homelab`, the key files and `/usr/local/bin/homelab` still exist
