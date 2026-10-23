# Design

## Context

Today three tools share the setup: chezmoi links the dotfiles (source names `dot_*`, conditions in `.chezmoiignore`, removals in `.chezmoiremove`, one create-once template for `~/.gitconfig.local`), Ansible installs packages, system configuration and also the user-space tools (roles `user_tools`, `node_tools`, `yazi`, `gh_cli`, `az_cli`, `git_min`, about 450 lines), and the `machine` CLI orchestrates them. The zsh and bash configuration needs tools that come from apt through Ansible (`fzf`, `jq`, `autojump`, `luajit`), so a host without root has no working shell tooling, and the background update has to stop before the first pending system commit.

Two spikes in a Ubuntu 24.04 container without root, with `mise` 2026.10.17 (released the day before), showed:

- Dotfile groups with real file names are linked file by file, a host selects groups in a local config, switching to fewer groups and applying with removal marks the dropped files as orphaned and removes only links into the repository, and two groups with the same target are reported before anything is written.
- Tool fragments in `conf.d/` install `fzf`, `zoxide` and `starship` without root in about 3 seconds from the aqua registry with checksums, one lockfile covers all fragments and includes `linux-arm64`, and `mise prune` removes the tools of a deleted fragment.
- `mise activate` works in bash and zsh and adds about 20 ms to shell start (measured in the container).
- A `copy` entry overwrites host edits, so a create-once file cannot be done with it.
- A group `root` that is relative starts at the dotfiles root of `mise` (default `~/.dotfiles`), not at the config file; the lockfile is written to `~/.config/mise/`.

See proposal.md for the motivation. This change builds on `simplify-machine-cli` (toolkit, local-overrides helper) and is archived after it.

## Goals / Non-Goals

**Goals:**
- A shell that works completely without Ansible and without root: dotfiles and every tool the shell needs come from `mise`.
- A `home/` that reads like the home directory: real file names, one directory per group, visible which files belong to which profile.
- Ansible limited to what needs root; a host without root still gets everything else.
- An update flow whose steps come from the file difference and that can always go to the upstream tip.

**Non-Goals:**
- Replacing zinit as the zsh plugin manager (the binary tools zinit fetched move to `mise`); that is done by `adopt-antidote-starship`.
- Replacing `bw` or changing Bitwarden handling (`simplify-machine-cli`, `openspec/backlog.md`).
- Changing the automatic revert after a failed zsh health check; it stays and the requirement keeps its behaviour, only the tool names in it change. Its use is counted by the event log of `simplify-machine-cli`.
- Moving system roles (`monitoring`, `thinkpad_tuning`, `sshd_home`, `touch_device`, `stylus_touch_guard`, apt packages) out of Ansible.

## Decisions

- **`mise` for dotfile groups and user-space tools.** Groups are directories with real file names; a group may carry a tool fragment next to its files. Both are selected by the same list of groups per host, so there is one selection logic and no second condition file. The `machine` CLI derives the list from the host's profile and features and writes it to the local `mise` configuration; `mise` does the linking, the removal of orphaned links, the conflict check and the tool install.
- **The CLI stays the orchestrator.** `mise` has no dependencies between groups and no root step, so the group selection, the system fingerprint and the order (dotfiles and tools, then Ansible) stay in `machine`.
- **Ansible keeps only root work.** User-space roles are deleted once the tools are in group fragments; a repository check fails when a tool is declared in a group fragment and in an Ansible package list, and when two groups declare the same tool.
- **`~/.gitconfig.local` is created by `machine setup`.** The profile defaults (identity, `safe.directory`) are written once when the file is missing. The Git include of the file already exists in the shared config and Git treats a missing include target as empty, so nothing has to guarantee its presence. Host-only keys that tooling adds to the shared file are handled by the local-overrides helper of `simplify-machine-cli`.
- **The background update works on the upstream tip.** On a clean checkout it fast-forwards, decides the steps from the files that differ between the old and the new revision (dotfile apply, tool install, shell refresh, system step) and applies the user part. The commit-by-commit classification and the search for a safe target commit are removed. This is safe because the shell no longer depends on a tool that only Ansible installs.
- **Pending system changes are a path filter, not `ansible --check`.** After each successful Ansible run the revision is stored as `ansible_applied_rev`. The files changed under `ansible/` and the host profile since then are filtered: playbooks, `tasks/`, `group_vars/` and the host profile always count; `roles/<r>/**` counts only when `<r>` is enabled for this host (role `when:` in `workstation.yml` evaluated against `profile` and `features`; a condition that cannot be evaluated counts as applicable); docs, `dump_*.yml` and the inventory are ignored. A host that has never run Ansible (no root) has no pending system update. `--check` was rejected: it needs root, which work machines do not allow, is slow and under-reports `shell` and `command` tasks.
- **Lockfile and updates.** Tool versions are pinned in one lockfile in the repository; tools are updated by a commit that changes the lockfile, so reproducibility and review stay with Git. `machine update --check` may list outdated tools but changes nothing.
- **Tools are reached through `mise activate`.** Interactive bash and zsh activate `mise`; shims are not used. The start-time cost measured in the spike is about 20 ms.
- **One state file** replaces the state file, the pending marker and the failed-revision file; the shell prompt segment keeps reading the update state as today.
- **One attention entry point.** `machine attention` collects every open item (pending Ansible update, conflicts, diverging values, new local text in a conflicting file, failed update) from the state file and the local-overrides helper and walks the user through them with the toolkit's prompts. Background runs only record items. Plain `machine` without arguments does the same; `machine attention` is the explicit form, there is no other alias.
- **fzf integration uses `fzf --zsh` and `fzf --bash`.** The configuration no longer searches distribution paths for key-bindings and completion files.
- **`machine` sets `MISE_DOTFILES_ROOT` to the checkout.** The spike showed that `mise -C <checkout>` alone does not move the dotfile root (it stays `~/.dotfiles` and the apply fails with "sources do not exist"); with the variable set, a checkout at any path works, links point at the real path, and re-applying after moving the checkout re-links everything.
- **`mise` is pinned to one release.** `mise` has no stable channel (every calendar-versioned release is a normal release, the dotfile workflow exists since 2026.6.6, `dotfile_groups` and `--prune-dotfiles` since 2026.10.x). `bootstrap` installs a pinned version (2026.10.17 tested); raising it is a commit.
- **The profile-to-groups mapping is derived in `machine`** from the host's profile and features (owner agreed with the recommendation). Alternatives not chosen: metadata per group, a central mapping file, a hand-edited per-host list.
- **Ansible stays for root work.** `mise bootstrap` could declare apt packages, system files, services and units, but it is weeks old and the Docker tests cover the Ansible roles; replacing the five root roles is a separate later change. `mise bootstrap plan --detailed-exitcode` (no root needed) is a candidate to replace the path filter then.
- **Git comes from the system for the first clone; `mise` always provides the user-space Git.** `./bootstrap` and `machine` assume a pre-installed `git` for the first clone. The shared `~/.gitconfig` needs Git 2.36 or newer (`includeIf hasconfig:remote.*.url`), so a user-space Git (`conda:git`, 2.56.0 in the spike, about 255 MB, no root) is installed on every host and replaces the `git_min` role. The shared config already carries the `filter "lfs"` section, so `git-lfs` (aqua) needs no system config.
- **Tools that must work outside interactive shells are on the shims path.** Git is also used by IDEs, hooks, cron and `ssh` commands that never run `mise activate`; `~/.zshenv` and `~/.profile` add the `mise` shims directory so those find the same Git. This is an exception to "no shims" and applies to Git and `git-lfs` only.
- **Existing hosts migrate by re-applying.** `machine setup` applies the groups with removal of orphans, then a sweep removes dangling symlinks whose old target lay inside the repository (the checkout or its former `dot_*` paths). The old chezmoi configuration and state may stay on the host: nothing runs chezmoi any more, so they have no effect; removing them is optional cleanup. No `migrate` subcommand is added (`update-flow` forbids one).
- **Shell extras come from `mise` tools or `[bootstrap.repos]`, not Ansible.** The shell fonts are Nerd Fonts fetched as a `github:` tool and linked into `~/.local/share/fonts`, and any plugin repository is cloned by `machine` or declared in `[bootstrap.repos]`. They are part of the shell and Git configuration, so `machine update` covers them like any other group tool.

## Alternatives considered

The owner asked for the comparison and decided to use `mise`; the reasons below are the ones found during the evaluation and are not separately confirmed:

- Keep chezmoi and add `mise` only for tools: lowest risk, but keeps `dot_*` names, the ignore file and `.chezmoiremove`.
- GNU Stow or an own linker plus `mise` for tools: removes the names problem, but adds a tool or code that `mise` already covers.
- Copier: a project scaffolder with three-way template merge; it does not produce live symlinks into a checkout.
- `aqua` or `ubi` instead of `mise`: both can be backends of `mise`, which also covers Node and Python runtimes.
- A group manifest with `requires` and a tool registry in `machine`: dropped for now; `mise` fragments per group already cover tool selection, and group dependencies are expressed by the profile selecting the groups.

## Risks / Trade-offs

- [The dotfile and bootstrap features of `mise` are one day old and from a single maintainer] → gate before the migration tasks: a stable release must contain them (see Open Questions); the group directories are plain files and stay portable to another linker.
- [A failed tool download in the background job] → the install fails, the checkout is reset by the existing safety net and the state is needs-attention; nothing is retried until the network or a manual update works.
- [Existing hosts hold chezmoi links into `dot_*` paths] → a one-time migration step in `machine setup` replaces them (see Open Questions).
- [Two tools could install the same binary] → repository check, and `mise` installs into its own directory so the order on `PATH` decides until the Ansible side is removed.
- [Large rename of `home/`] → one commit that only moves files, so history follows the files, before any content change.

## Migration Plan

1. Spike gate: confirm the `mise` release, the group `root` setting and the lockfile location against the real repository in a container (see Open Questions).
2. Tools first: fragments for the shell tools, lockfile, `fzf --zsh`/`--bash` in the configuration, `mise` activation in the shell files and bootstrap. Ansible still runs and its user-space roles are removed only after the tool group works on every profile.
3. Dotfile groups: move `home/` into groups (rename-only commit), write the group selection from profile and features, replace the chezmoi apply by the `mise` apply, add the one-time migration, create `~/.gitconfig.local` in `machine setup`, remove the chezmoi files and install step.
4. Update flow: file-difference steps, upstream tip, relevance filter, one state file, `machine attention`.
5. Specs, Readme and tests follow each step.

Rollback before step 3 is a revert of the tool commits. After step 3 a host can be restored with the previous commit and chezmoi; the migration step keeps a list of the links it replaced.

## Open Questions

- Which `mise` release do we pin? 2026.10.17 passed the spike (any-path checkout, removal, re-link after a move); task 0.1 repeats it with the real repository.
- Task 0.1 result (container, user 1000, no root, `mise` 2026.10.17, real files of this repository laid out as groups `core` and `work`, checkout at `/tmp/some/where/else/dotfiles`):
  - Apply with `MISE_DOTFILES_ROOT` set links every file and symlinks point into the checkout.
  - Selecting only `core` and applying with `--prune` removed `~/.tmux.conf` (group `work`) and nothing else.
  - After moving the checkout, a re-apply with the new `MISE_DOTFILES_ROOT` re-linked everything to the new path.
  - New finding: `mise` refuses a config file in the checkout that is not trusted (`Config files ... are not trusted`); `machine` must run `mise trust` on the checkout's `mise` config before the first apply or tool install, and again after the checkout moves.
  - Lockfile: with the project config in `<checkout>/mise/` (`config.toml` plus `conf.d/*.toml`) and `lockfile = true`, `mise lock --platform linux-x64,linux-arm64` writes `<checkout>/mise/mise.lock`, so it lives in the repository. The group list stays in `~/.config/mise/config.local.toml`.
- Tools and their source (spike: installable without root; trust is my assessment, not owner-confirmed):
  - aqua registry (checksums, upstream releases): `fzf`, `zoxide`, `eza`, `fd`, `starship`, `jq`, `gh`, `yazi`, `git-lfs`, `bat`, `ripgrep`; Node is a core tool.
  - `tmux`: `aqua:tmux/tmux-builds`, published from the official `tmux` GitHub organization, static Linux build. Decided: tmux comes from `mise`; the registry entry has no checksum step, so the version is pinned.
  - `az_cli`: decided: `pipx:azure-cli` with `uv` on the profiles that list it (25 s, 371 MB, brings its own Python); the deb was not compared (needs the Microsoft apt repository and root).
  - Stay in apt/Ansible (not in the `mise` registry): `zsh`, `gnupg`. Drop: `autojump` (zoxide replaces it) and `luajit` (not verified whether anything uses it).
- Git from `conda:git`: it ignores `/etc/gitconfig` (it reads `<prefix>/etc/gitconfig`) and uses its own CA bundle, so work hosts need `http.sslCAInfo` in `~/.gitconfig.local`. Can `machine setup` seed it on work hosts? (Decided: the Git group is always selected, on every host.)
- Bash on hosts without zsh: decided in `investigate-shell-plugin-manager` and implemented by `adopt-antidote-starship`: `starship`, `zoxide` and `fzf --bash` (fallback level), no ble.sh (about 300 ms startup, no stable release).
- Fonts: the owner chose Fira Code Nerd Font and wants the dotfiles to set it in the terminals used: Guake and the VS Code terminal (Windows is out of scope). Guake keeps the font in `gsettings` (`guake.style.font style`, currently `'Monospace 10'`, checked on this host), which a script can set after the font is installed. VS Code needs `terminal.integrated.fontFamily` in its `settings.json`; the file is a whole-file user setting that VS Code also writes, so a merge of that one key (mise dotfile edit modes are documented for parts of a file, not verified for JSON) must be spiked. The font is drawn by the terminal on the machine you sit at: an SSH session uses the local terminal's font, so the remote dotfiles cannot and need not set it. For VS Code Remote-SSH the integrated terminal font is a client-side user setting (not verified).
- Fresh shell after `machine update` (decided, owner confirmed): a child process cannot reload its parent shell, so a `machine` shell function (zsh and bash) runs `exec` on the current shell after a successful `machine update`. Alternatives: only the prompt segment tells the user to reload (today); `machine update` starts a new shell as a child (nested, rejected).
- Zinit versus a lighter plugin manager (`antidote`, `sheldon`): decided later; kept for now.
- `sde` and `sdx`: inside the container `bootstrap --profile container --no-become` runs as today; a persistent `~/.local/share/mise` cache mount next to the antidote cache avoids re-downloading tools (not spiked).
