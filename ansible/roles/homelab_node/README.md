# homelab_node

Feature `homelab-node` (optional on private servers): base of a homelab Docker Compose
host. User-facing description: [docs/features.md](../../../docs/features.md#homelab-compose-host-feature-homelab-node).

Inputs (extra vars from `machine`, see `machine_cli/homelab_node.py`):

- `homelab_node`: resolved `homelab:` block of the host config (`host`, `user`, `clone`,
  `managed_clone`, `ci_restrict`, `problems`). Without it (remote runs) the role uses the
  short hostname, the login user (`ditschi` for root) and `/opt/homelab`.
- `homelab_age_private_key`: the hidden field `private_key` of the Bitwarden item
  `homelab-age-<host>`, only when it could be read. Every task that touches it has
  `no_log`.

What it does, in order: refuse a root deploy user; apt `git python3 python3-yaml
openssh-client`; create the deploy user when missing (locked password, no sudo);
`authorized_keys` (keys of `ssh_allow_from`, CI key with the forced command
`/usr/local/bin/homelab-ci`, existing CI entry only with `ci_restrict`); sops from the
GitHub release with the sha256 in `defaults/main.yml`; GitHub host keys; age key file;
deploy key, acceptance check with the deploy key alone and clone of `main`; links
`/usr/local/bin/homelab` and `hl`; `docker` group; tool checks, including `sops` as a
non-interactive SSH session of the deploy user sees it. Findings go to
`/var/lib/machine/homelab-node.json` (no secrets) for `machine attention`.

Never: Docker commands other than `docker --version` and `docker compose version`,
reboots, paths under a data root, fetch/reset/checkout of an existing clone, removing
other sops installations.

Updating sops: change `homelab_node_sops_version` and both checksums from
`sops-v<version>.checksums.txt` of the release. GitHub host keys:
`files/github_known_hosts` from `https://api.github.com/meta` (`ssh_keys`).

No Bash or Zsh completion: neither the homelab CLI nor sops ships one.
