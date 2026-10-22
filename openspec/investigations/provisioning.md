# Investigation report: baseline-provisioning

Read-only research for investigations 1-6 of the archived change `2026-10-22-baseline-provisioning` (design.md). Item 7 (test policy) is handled elsewhere. Nothing was changed in code. Decisions stay with the owner. Items marked "unverified" were read from files only and not run.

## 1. Provisioner comparison

**Findings**
- Size of the current setup (verified by reading): `ansible/workstation.yml` has 11 plays; `group_vars/all.yml` holds the package table `packages_by_feature`; 11 local roles; six profile files in `ansible/profiles/`; one collection (`ansible.posix`, `requirements.yml`). Desired state per host is `machine/hosts/<host>.yml` (feature list). The `machine` CLI wraps `ansible-playbook` (`tools.py run_ansible`).
- What the repo actually does with Ansible: apt installs, file/template deploys, systemd units, udev/sysctl/grub drop-ins, and many `command`/`shell` tasks with `creates:` or hand-written `changed_when` (for example `node_tools`: nvm/npm via `bash -c`; `yazi`, `gh_cli`, `git_min`: version checks and apt repos). So a good part of the idempotence is hand-written, not provided by modules.
- Ansible needs to be installed on every host that applies locally (`machine` checks `ansible_works()` in `system.py`; Readme quick start bootstraps it) and `ansible.posix` via `ansible-galaxy`. Updates: `machine update`/`apply` re-run the playbook; remote use works via inventory + SSH (`--limit`).
- Existing-installation preservation (spec) is implemented as explicit checks in the playbook; this logic would be needed in any tool.

Short comparison for this repo (general knowledge, unverified against a prototype):
- **Ansible (current).** Readable YAML, declarative modules for apt/file/systemd/template, idempotent by design where modules exist, check mode, built-in remote execution over SSH, no daemon. Cost: Python plus ansible-core on every managed host (heavy for a Pi Zero and containers), YAML+Jinja gets awkward for logic (see `workstation.yml` Docker block), and the shell tasks are not really declarative. Learning curve is moderate; the repo already has the structure and CI lint (`ansible-lint`).
- **Plain scripts (bash/Python).** No extra dependency, trivially readable to anyone who knows shell, small footprint. Idempotence, check/dry-run, ordering and error handling must be written by hand; this grows into a home-made Ansible. Remote runs via `ssh host script`. Fits best for a small, stable set of steps.
- **Nix + home-manager (or NixOS).** Strongest idempotence and rollback, one declarative language for packages and dotfiles, reproducible. Cost: a new language and large learning curve, does not manage Ubuntu/Raspberry Pi OS system files (apt, sshd, udev, grub, systemd units) without NixOS or system-manager, conflicts with chezmoi symlink mode and the existing `machine` CLI, and corporate work machines without root may not allow a Nix install. Mismatch for the system half of this repo; fits only the user-level part (NVM, CLIs, dotfiles).
- **Others.** Chezmoi `run_` scripts (already used for dotfiles; good for user-level, no remote story). Pyinfra (Python instead of YAML, SSH-based, no remote agent, idempotent operations; smaller community). Salt/Puppet/Chef: agent/server model, too heavy. Containers/images: do not fit laptops.

**Suggestion:** keep Ansible for now. Reason: the system half (apt, sshd, systemd, udev, grub) is what Ansible modules do best, the code and CI exist, and the other options either rebuild that part by hand or do not cover it. To ease the learning curve, keep roles thin, keep logic in the CLI/Python where it is testable, and prefer modules over `shell`. If a real alternative is wanted, prototype only pyinfra or Nix/home-manager for the user-level `node_tools`/`user_tools` roles and compare against the Ansible version before deciding.

## 2. Privileged route for managed work machines

**Findings**
- Readme (lines 186-192) states the playbook needs approval to run Ansible modules as root; `--no-become` only suppresses the password prompt. Without root, fact gathering fails with "not allowed to execute" and no play runs (verified in Readme; behaviour on a real work host unverified). `ansible.cfg` has `become = False` globally, so root comes only from the plays.
- Plays with `become: true` in `workstation.yml` (verified): `packages` (apt install of `packages_base`/`packages_host`/`packages_work`/feature packages, Docker provider checks), `monitoring`, `git_min`, `yazi`, `gh_cli`, `az_cli`, `stylus_touch_guard`, `thinkpad_tuning`, `sshd_home`. The `monitoring` role has its own `become: true` on 7 tasks.
- Plays without root: `node_tools` and `user_tools` (user-local installs in `~/.nvm`, `~/.local/bin`, `~/.local/share/fonts`) and `touch_device` (GNOME extensions as the login user).
- Root needs by role (from tasks, verified by reading):
  - packages/Docker/`etckeeper`/`unattended-upgrades`/`syncthing`/`kerberos`/`gnome`: `apt`.
  - `git_min`: `/etc/apt/keyrings`, `/etc/apt/sources.list.d`, apt upgrade of git.
  - `gh_cli`: apt keyring and source list, apt install `gh`.
  - `az_cli`: official installer script (root).
  - `yazi`: `apt deb:` install of a downloaded `.deb`.
  - `monitoring`: telegraf package, `/etc/telegraf`, service enable.
  - `sshd_home`: `/etc/ssh/sshd_config(.d)`, `authorized_keys` for the user, validation.
  - `stylus_touch_guard`: `/usr/local/lib/machine`, systemd unit.
  - `thinkpad_tuning`: `/etc/udev`, `/etc/systemd`, `/etc/sysctl.d`, `/etc/default/grub.d`, `/usr/local/bin`, zram.
- Work-machine profile (`profiles/work-machine.yml`) selects `kerberos` (apt `ldap-utils`, `krb5-user`), `azure-cli`, `gh-cli`, `gnome`, `yazi`, `etckeeper` and the base packages: all need root. Only `node_tools`, `user_tools` and `touch_device` would run without it.

**Suggestion:** do not try to bypass the restriction. Options to compare with the administrator: (a) skip all root plays when `sudo -n true` or a root probe fails and run only the user-level plays (`node_tools`, `user_tools`); (b) ask for an approved route (a sudoers entry for the exact playbook, or IT-managed packages for `krb5-user`, `ldap-utils`, `azure-cli`); (c) keep the current behaviour, which fails early. Reason: (a) is a small change that matches the spec sentence "dotfiles still usable, system roles not applied", but makes the failure silent if not reported clearly; user-level alternatives to root tasks (`yazi` and `gh` as user-local binaries) are possible but duplicate the preserved-installation logic. Confirm with the owner what the work machine allows before designing.

## 3. Node per profile

**Findings**
- `node_tools` runs in its own play without `when:` on every profile (`workstation.yml`; verified). It installs NVM `v0.40.3`, Node LTS and npm into the user home (`roles/node_tools`).
- Node-based tools in the repo (verified in `node_tools/defaults/main.yml` and tasks): `@anthropic-ai/claude-code` (feature `claude-code`), `@github/copilot` (feature `copilot-cli`), `@fission-ai/openspec` (installed when either feature is selected or any existing LLM command is found). No other role or package table entry needs Node (grep over `ansible/`).
- Per profile (default features): `home-laptop`, `home-server`, `rpi`, `rpi-zero`: `claude-code` + OpenSpec; `work-machine`: `claude-code`, `copilot-cli`, OpenSpec; `container`: none, so Node is installed with nothing using it (unless a user adds an LLM feature or has an existing CLI). `ci-container.yml` host exists in `machine/hosts/`.
- `rpi-zero`: Readme says ARMv6 cannot run current official Node, so provisioning fails there (documented; the profile still defaults to `claude-code`). Unverified: whether this makes `machine apply` fail on that profile in practice.
- Shell startup loads NVM in bash and zsh (Readme); a cost on every shell start (unmeasured).
- Container needs Node also for nothing else at runtime in the repo.

**Suggestion:** run `node_tools` only when a Node-based tool is needed: an LLM feature is selected or an existing LLM CLI is found. Reason: containers (and hosts without LLM CLIs) would skip a large download and the NVM shell hook, and `rpi-zero` would stop failing on Node. The spec "Node tools on every profile" would need a change, so this is a decision for the owner; an alternative is to keep it everywhere and just remove `claude-code` from `rpi-zero`.

## 4. OpenSpec as an explicit feature

**Findings**
- Current rule (`node_tools/tasks/main.yml`, verified): OpenSpec (`@fission-ai/openspec`) is installed globally via npm if not yet present and (a selected feature is in `node_tools_cli_packages`, or any command in `node_tools_llm_commands` already exists). The existing-command list includes `codex`, `gemini`, `aider`, `ollama`, which are not features of this repo.
- It cannot be disabled while an LLM CLI is present. It does not appear in the feature picker (`core.py` feature list) or in the Readme feature list; only the Node section of the Readme mentions it.
- Maintenance cost today: one condition in one task file. An explicit feature would add one entry in `core.py`, the Readme feature list, the profiles/host files and `node_cli_packages` (it would then need an `item.feature` entry like the LLM CLIs).

**Suggestion:** if the dependency should be visible, add an `openspec` feature in `core.py` and `node_cli_packages`, defaulted on in profiles that default to an LLM CLI (profile default), and drop the "already installed" detection. Reason: lowest maintenance, visible and switchable in `machine setup`, and the install no longer depends on unrelated commands such as `ollama`. The conditional install is cheapest but hides the relationship; a plain explicit feature without a default would make it unavailable by surprise.

## 5. Purpose of `etckeeper`

**Findings**
- Introduced in commit `292e505` ("Add etckeeper feature, enabled by default on every profile", 2026-10-07, author Christian Ditscher). Recorded evidence (commit message): "/etc becomes a local git repository that etckeeper commits around each apt run and daily. Added to the default feature list of all profiles that run ansible (not container) and to the versioned host files." This states the mechanism, not a motivation.
- `git log -S etckeeper` shows only that commit as introduction; later hits (`9d5d555` profile rename, `13ec602`, `e8534c0`, `32fc6cb`) touch the word incidentally, not for reasons. No comment, doc or Readme explains why. `group_vars/all.yml` comment: "/etc as a local git repository; commits around every apt run and daily". `core.py`: "Keep /etc in a local git repository (history of system config)". `tests/integration/test_host_yaml_install.py` asserts the package is installed. No `docs/decisions` entry exists.
- Behaviour/cost (general knowledge, unverified here): etckeeper stores file permissions and may store secrets in `/etc` (for example Kerberos keytabs, ssh host keys, wpa/NetworkManager connections) in `/etc/.git`, readable by root only; the repository grows with every apt run. It is local only, no remote.
- Hypothesis (not confirmed by the owner): the owner wanted a history of system config changes, in particular for the files written by `thinkpad_tuning` and `sshd_home` and for the Pi/server hosts. Do not treat this as the reason.

**Suggestion:** ask the owner for the reason and record it as `[owner]`. Meanwhile keep it. If the reason is only "history of changes by Ansible/apt", consider limiting it to hosts where `/etc` is changed (`home-server`, `rpi`, `home-laptop` with `thinkpad-tuning`) and off for `work-machine`, where `/etc` has Kerberos/corporate configuration, and for `rpi-zero` (small SD card). Reason: lower risk and storage cost; but the spec says all non-container profiles, so this needs an owner decision.

## 6. Remote updates

**Findings**
- Inventory (`ansible/inventory/hosts.example.yml`, verified): groups `laptops`, `servers` (`homeserver`, `netmaster` with port 5115), `rpis` (`netmaster`, `rpi-zero-1`), empty `work`. Real `hosts.yml` is vault-encrypted (`machine inventory encrypt`; vault password in Bitwarden); not read here. `netmaster` is in two groups. `inventory/local.yml` is the local default.
- `machine apply --limit homeserver` runs `ansible-playbook` from the laptop over SSH using the host file `machine/hosts/<host>.yml` (`commands.py` remote path, Readme lines 169-180). Remote runs do no auto-revert on failure. `machine update` is local: pull, sync profile, apply on drift, and update marker/timer `dotfiles-update-check.timer` (`commands.py`). It does not update other hosts.
- Remote apply covers system roles and `node_tools` (via SSH as `ansible_user`); the dotfiles on the remote host are not updated by `apply --limit` (unverified: whether the remote repo pull happens; the code shows only an Ansible run).
- `become` on remote hosts needs sudo; the CLI uses `--ask-become-pass` only on a TTY (`tools.py`), so unattended remote runs need passwordless sudo (`passwordless_sudo()` exists). `unattended-upgrades` already handles OS package updates on servers and Pis.
- `homelab.yml` is a stub; it does not update hosts.

**Suggestion:** add a thin `machine update --host <name|group>` (or `--all-servers`) that runs on the control machine: SSH to the host, `git pull` the dotfiles repo there, then `machine apply --limit`, with a summary per host. Reason: it reuses inventory and Ansible and avoids a manual login. Preconditions to check: passwordless sudo or a become password route on servers, vault password access on the control node, and a failure policy (continue with the other hosts, no auto-revert). A pull timer on each host is an alternative that needs no control node, but it adds a service per host and is less visible.
