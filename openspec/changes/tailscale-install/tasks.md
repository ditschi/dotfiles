# Tasks

## 1. Ansible role

- [x] 1.1 Add `ansible/roles/tailscale/` (defaults, `files/tailscale.asc` with the pinned key, `templates/tailscale.sources.j2`, `tasks/main.yml`, README) following `cosmic_desktop`: distro mapping, Release HEAD check, warning when unsupported, with a snap installed install nothing and print the hint, remove `tailscale.list`, install `tailscale`; verify with `ansible-lint ansible/*.yml`
- [x] 1.2 Run the role from `ansible/workstation.yml` when `'tailscale' in machine_features` (tag `tailscale`); verify with `ansible-playbook --syntax-check ansible/site.yml`
- [x] 1.3 Add `tests/unit/test_tailscale.py`: pinned key fingerprint, source template contents (`Signed-By` the key path, URI per distro), role wired behind the feature; verify with `pytest tests/unit/test_tailscale.py -q`

## 2. Setup message and completion

- [x] 2.1 Change the missing-binary log in `maybe_tailscale_login` (`machine_cli/ssh_keys.py`) and cover it in `tests/unit/test_host_profiles.py`; verify with `pytest tests/unit/test_host_profiles.py -q -k tailscale`
- [x] 2.2 Add the cached `tailscale completion` lines to `home/core/.shell/zsh/plugins.zsh` and, inside the bash-completion guard, to `home/core/.shell/bash/tools.bash`; verify `tailscale <TAB>` completes in a new zsh and bash, and that bash without bash-completion starts without errors
- [x] 2.3 Update the feature help in `ansible/group_vars/all/features.yml` if needed and describe the feature in `docs/features.md` (repository, snap kept, manual move, undo); verify `pytest tests/unit/test_features.py -q`

- [x] 2.4 Add `tailscale` to the features of `machine/hosts/netmaster.yml` and `machine/hosts/homeserver.yml`; verify `pytest tests/unit/test_host_profiles.py -q`

## 3. Validation

- [ ] 3.1 Move the ThinkPad by hand (README commands), run `machine update`, and confirm: `dpkg -l tailscale` installed, same name and IP, no login prompt; a second run changes nothing; after `machine update` on netmaster and homeserver, `tailscale version` works there and `sudo tailscale up` logs them in
- [x] 3.2 Run `pre-commit run --files <changed paths>`, then `openspec validate tailscale-install --strict`
- [x] 3.3 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change adds a shared Ansible role and touches the setup flow; fix findings

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
