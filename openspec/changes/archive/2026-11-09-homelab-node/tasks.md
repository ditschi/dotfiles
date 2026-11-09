# Tasks

## 1. Feature and host config

- [x] 1.1 Add `homelab-node` to `ansible/group_vars/all/features.yml` (help text, no groups, `work: excluded`, `desktop: excluded`, `container: excluded`, `server: optional`) and extend `tests/unit/test_features.py` with the menu scenarios of the `feature-selection` delta
- [x] 1.2 Accept and preserve the optional `homelab` block (`host`, `user`, `clone`, `ci_restrict`) in `machine_cli/profile.py` on parse, setup rewrite, `machine host save` and takeover, like `disk_space`. Pass it to Ansible as `homelab_settings`. Add tests in `tests/unit/test_host_profiles.py`
- [x] 1.3 Resolve the effective settings in one place (host: `homelab.host` or `hostname -s`, refusing `key`; user: `homelab.user`, else the login user, else `ditschi` when `machine` runs as root; `root` refused; clone: `homelab.clone` or `/opt/homelab`), with unit tests for oracle, contabo and homeserver

## 2. Bitwarden handover

- [x] 2.1 Read `homelab-age-<host>` (hidden field `private_key`) in `machine_cli/bw_client.py` before Ansible when the host has `homelab-node`. Add `homelab_age_private_key` to the private extra-vars file in `machine_cli/tools.py`, which is removed after the run. Never log the value
- [x] 2.2 Missing Bitwarden, item or field: log the item name and continue, with no prompt without a terminal. Unit tests in `tests/unit/test_bw_and_answers.py` (or a new `test_homelab_node.py`) cover read, missing item, missing field, a host without the feature, and no value in env files or logs

## 3. Ansible role `homelab_node`

- [x] 3.1 Create `ansible/roles/homelab_node/` (defaults with the sops version and the per-arch sha256 from the v3.13.3 checksums file, GitHub known hosts file, README) and a play in `ansible/workstation.yml` with `when: "'homelab-node' in machine_features"`, tag `homelab`
- [x] 3.2 Refuse `root` as deploy user (skip the rest and record it). Create the deploy user when missing: home directory, the login user's shell, locked password, no sudo. Never change an existing user's password, shell or groups (other than adding `docker` in 3.10)
- [x] 3.3 Add to the deploy user's `authorized_keys` (additive, `exclusive: false`) the `machine/ssh_keys/<host>.pub` keys for `ssh_allow_from` (same resolution as `roles/sshd_home`) and `machine/ssh_keys/homelab-ci.pub`. Install `/usr/local/bin/homelab-ci` (accepts only `homelab deploy <7-40 hex>` from `SSH_ORIGINAL_COMMAND`, execs `/usr/local/bin/homelab deploy <sha>` without a shell, else exits non-zero). Add the CI key with `restrict,command="/usr/local/bin/homelab-ci"` only when it is missing; replace the options of an existing entry only with `homelab.ci_restrict: true`. Report missing key files and record an unrestricted CI entry. Unit tests for the wrapper (accepted sha, short/long/non-hex sha, extra arguments, shell metacharacters, empty command)
- [x] 3.4 Install the packages git, python3 and python3-yaml. Install `/etc/ssh/homelab_github_known_hosts`
- [x] 3.5 Download sops for `ansible_architecture`, check the sha256, install to `/usr/local/bin/sops` (755). Skip when the installed version is 3.13.3; never install on a mismatch
- [x] 3.6 Write the age key (`no_log`) to `~deploy/.config/sops/age/keys.txt` (dir 700, file 600, owned by the deploy user), only when the file is missing or holds no `AGE-SECRET-KEY-` line. Record "differs" when it holds another key
- [x] 3.7 For the default clone path only: create `~deploy/.ssh/homelab_deploy_ed25519` once (ed25519, mode 600, comment `homelab-deploy@<host>`). Test acceptance with `git ls-remote` (deploy key only, `IdentityAgent=none`). When accepted and no repo exists, clone `main` to `/opt/homelab` as the deploy user. Otherwise print the public key with the GitHub hint. Set `core.sshCommand` on the clone; never fetch, reset or switch an existing clone
- [x] 3.8 For another clone path: check that it is a git repository and record it when it is not; no git changes
- [x] 3.9 Create the symlinks `/usr/local/bin/homelab` and `/usr/local/bin/hl` to `<clone>/scripts/homelab.py`
- [x] 3.10 Add the deploy user to `docker` (append) when the group exists. Record whether `docker` and `docker compose version` work
- [x] 3.11 Record `command -v sops` and `sops --version` from the deploy user's emulated non-interactive SSH environment (login shell `-c`, clean env, `SSH_CLIENT` set)
- [x] 3.12 Write `/var/lib/machine/homelab-node.json` (644, no secrets) with all recorded findings and the run time
- [x] 3.13 Role unit test in the style of `tests/unit/test_monitoring_role.py`: forbidden commands (`docker … up|down|restart|rm|stop|start|prune`, `reboot`, `systemctl restart docker`) and data root paths do not appear, the age key task has `no_log`, and the pinned checksums exist for amd64 and arm64

## 4. machine attention

- [x] 4.1 Read the status file in `machine_cli` and add attention items: deploy user problem, missing `homelab-ci.pub` or `ssh_allow_from` key files, an unrestricted CI key entry once the clone exists (hint: set `homelab.ci_restrict: true` after CI uses `homelab deploy`), missing `homelab-age-<host>`, key file differs, deploy key not accepted (with the public key and the GitHub hint), `sops` not 3.13.3 for the deploy user (path that wins), missing Docker or Compose, existing checkout path without a repository. Each item names `machine apply` as the next step
- [x] 4.2 Unit tests for each item and for a host without the feature (no items, status file ignored)

## 5. Docs

- [x] 5.1 `docs/features.md`: feature `homelab-node`, what it sets up, the first-run flow (apply → add the deploy key in GitHub → apply), and that deselecting removes nothing
- [x] 5.2 `docs/secrets.md`: item `homelab-age-<host>` in the item table. `docs/host-config.md`: the `homelab` block with examples for oracle, contabo and homeserver, and the fresh-VM flow (bootstrap as root → deploy user `ditschi`). `machine/ssh_keys/README.md`: `homelab-ci.pub`. Role README
- [x] 5.3 Completion: `homelab`/`hl` come from the homelab repo. Note in the role README that it provides no Bash or Zsh completion. sops ships none either

## 6. Validation

- [x] 6.1 Targeted tests: `pytest tests/unit/test_features.py tests/unit/test_host_profiles.py tests/unit/test_bw_and_answers.py tests/unit/test_homelab_node.py -q`, plus the attention tests
- [x] 6.2 `pytest tests/unit -q` (changes `machine_cli` profile parsing, the Bitwarden handover and attention, which are shared infrastructure)
- [x] 6.3 `ansible-lint ansible/*.yml`
- [x] 6.4 Role run in `machine testenv` or the Docker integration setup with the feature on (`--check` first, then a real run against a stub clone path), checking idempotence with a second run that reports no changes
- [x] 6.5 `pre-commit run --files <changed paths>` including untracked files
- [x] 6.6 `openspec validate homelab-node --strict`
- [x] 6.7 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent) and fix findings before archive

## Workflow follow-up

- Owner, before the first host: commit `machine/ssh_keys/homelab-ci.pub` (public half of `COMPOSE_SSH_KEY`).
- Owner, per host after merge: set the `homelab` block and the feature in `machine/hosts/<host>.yml`, `machine apply`, add the printed deploy key in GitHub (write access off), `machine apply` again (order: contabo, oracle, homeserver, see design.md Migration Plan).
- Owner, after CI uses `homelab deploy`: set `homelab.ci_restrict: true` on contabo and oracle, `machine apply`.
- Archive with spec sync after the first host runs.
