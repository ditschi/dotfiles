# Proposal

## Why

The setup splits what a shell needs across two tools. Tools that zsh and bash plugins depend on (`fzf`, `zoxide`, `eza`, `fd`, `starship`, `jq`, Node) come from Ansible, which needs root, so a host without `sudo` has no working shell tooling and an automatic update has to hold back home changes until Ansible has installed the matching tool. Dotfiles are applied by chezmoi, whose `dot_*` names make `home/` hard to read, whose ignore file hides which files belong to which profile, and which needs `.chezmoiremove` to remove files.

`mise` (one tool, no root) can install the user-space tools from one lockfile and can link dotfile groups with real file names, select groups per host, remove files that are no longer wanted and report conflicts before writing. Using it for both makes the shell work without Ansible, so Ansible is left with system packages and system configuration that need root, and the automatic update becomes simpler.

## What Changes

- Install every tool that the shell configuration needs, and the other user-space tools, with `mise`, from one fragment per group and one lockfile; remove the Ansible roles `user_tools`, `node_tools`, `yazi`, `gh_cli` and the user-space part of `az_cli` and `git_min` where `mise` provides the tool; keep Fonts as a small user-space step. The apt-only parts stay in Ansible and run only with root.
- Replace chezmoi by `mise` dotfile groups: `home/` is split into group directories with real file names (`.zshrc`, no `dot_*`), a host selects its groups from its profile and features, and files of a group that is no longer selected are removed. `.chezmoiignore`, `.chezmoiremove`, `.chezmoi.yaml.tmpl` and the chezmoi install step go away.
- Create `~/.gitconfig.local` once from the profile in `machine setup` instead of through a chezmoi template; Git ignores a missing `[include]` target, so no tool has to create it later.
- Rework the update flow on top of this: a background run fast-forwards a clean checkout to the upstream tip, then runs `mise install` and the dotfile apply with removal; pending Ansible changes are only reported, and only when they apply to this host (path filter against the host profile and the enabled roles, last applied revision stored after each Ansible run); the step decision comes from the file difference between the current and the target revision; one state file replaces state file, pending marker and failed-revision file.
- Add `machine attention` (also plain `machine`) as the one entry point that lists and walks through everything needing manual action: pending Ansible update, conflicts, diverging values and a failed update.
- Install `mise` from `./bootstrap` and keep its shell activation in `~/.bashrc` and `~/.zshrc` so tools are on `PATH` for interactive shells.
- **BREAKING**: the layout of `home/` and the tool that applies it change; hosts re-run `machine setup` once after the update that brings this change.

## Capabilities

### New Capabilities
- `user-tools`: user-space tools installed by `mise` without root, selected per group, pinned by one lockfile, removed when their group is no longer selected.

### Modified Capabilities
- `repo-layout`: dotfiles are applied as `mise` dotfile groups with real file names; the responsibilities and the "not deployed" requirement name `mise` instead of chezmoi.
- `update-flow`: file-difference based steps, background update to the upstream tip, relevance filter for system changes, one state file, `mise` instead of chezmoi in the safety net, and the attention entry point.
- `system-provisioning`: Ansible is limited to system roles that need root; the user-space roles and the Node role move to `user-tools`.
- `work-private-separation`: work modules are part of a group that only the `work-machine` profile selects.
- `git-config`: `~/.gitconfig.local` is created once by `machine setup` from the profile.
- `bootstrap`: bootstrap installs `mise` in addition to `uv`.

Affected profiles: all. The `container` and `rpi-zero` profiles select fewer groups; a work machine without root gets all user-space tools and the dotfiles without Ansible.

## Impact

- Code: `home/` (renamed into group directories), `ansible/roles/`, `ansible/group_vars/all.yml`, `ansible/profiles/`, `machine_cli/` (`updates.py`, `profile.py`, `tools.py`, `auto_update.py`, `commands.py`), `bootstrap`, `home/dot_zsh/config/02_plugins.zsh` (fzf key bindings through `fzf --zsh`), `tests/unit/` and the Docker tests.
- Dependencies: `mise` (released 2026.10.17 or newer; the dotfile and bootstrap features are new, see the design).
- Specs: the six above plus the new `user-tools`; `zsh-plugins` and `zsh-config-loading` keep their requirements.
- Related changes: builds on `simplify-machine-cli` (the local-overrides helper supplies the conflicts shown by `machine attention`; the toolkit and the state handling are reused). Archive `simplify-machine-cli` first.
