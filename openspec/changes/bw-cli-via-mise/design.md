# Design

## Context

`ensure_bitwarden_cli` in `machine_cli/tools.py` downloads `bw-linux-<ver>.zip` for a hard-coded version (2024.12.0) from the `bitwarden/clients` GitHub release, checks it against `bw-linux-sha256-<ver>.txt` and copies `bw` to `~/.local/bin`. On any CPU other than x86_64 it refuses, based on the comment "Bitwarden publishes a Linux CLI build for x86_64 only". It is called by `ensure_bootstrap_tools` (`machine setup`, not on containers) and by `require_bitwarden` after the "Install it now?" question (`machine env pull` and other explicit commands).

Facts checked on 2026-10-31:

- Since `cli-v2026.3.0` the release also has `bw-linux-arm64-<ver>.zip`. Since about `cli-v2025.6.0` the release has no `*-sha256-*.txt` files, so the current checksum step would also fail for any newer version on x86_64.
- The mise registry maps `bitwarden` to `aqua:bitwarden/clients`; for versions after 2026.1.0 the aqua entry selects `bw-linux-arm64-<ver>.zip` on linux/arm64.
- Spike (x86_64, mise 2026.10.15): with `bitwarden = "latest"` in a copy of the `core` fragments, `mise lock --global --platform linux-x64,linux-arm64 bitwarden` wrote `bitwarden@2026.10.1` with a sha256 checksum and URL for both platforms; `mise install bitwarden` installed it in 14 s and `bw --version` printed `2026.10.1`.
- Spike: with `MISE_CONFIG_DIR` set to the repository's `home/core/.config/mise` and an empty home, `mise install jq` installed exactly the locked version (1.8.2) before any dotfile link existed.
- In `machine setup`, `setup_bitwarden` runs before `write_dotfile_groups`, Ansible, `run_dotfiles_apply` and `run_tools_install`, because the Influx credentials must be read before Ansible (`secret-tools`). On a fresh host `~/.config/mise` is therefore not linked yet when `bw` is first needed.

## Goals / Non-Goals

**Goals:**
- One install path for `bw` on x86_64 and aarch64, with version and checksum in `mise.lock`.
- `bw` is present early enough in `machine setup` for the Bitwarden step.

**Non-Goals:**
- Replacing `bw` with `rbw` or another client (`simplify-machine-cli`, backlog).
- Changing the Bitwarden login, unlock or session handling.
- Removing a `bw` installed outside `~/.local/bin` (for example `/usr/local/bin/bw` or a snap).

## Decisions

- **`bw` from `mise` (`aqua:bitwarden/clients`), owner decision.** The owner asked for the option that works the same on every host and is easiest to maintain, and chose this one. The same mechanism already installs `gh`, `fzf`, `starship` and the other user tools; mise picks the right asset for the CPU, `mise.lock` holds version and checksum for both platforms, and an update is `mise upgrade` plus a reviewed lockfile commit. The custom download code in `machine` (and the version hard-coded in Python) goes away. This replaces the earlier choice of `~/.local/bin`, which was taken without a recorded reason.
  - Rejected: keeping the own installer and adding the arm64 asset. The version would stay hard-coded in Python, and since the release no longer ships checksum files, new code would be needed to read the asset digest from the GitHub API.
  - Rejected: the npm package `@bitwarden/cli` on the mise Node. It works on every CPU (plain JavaScript, Node ≥ 22), but every `bw` call starts Node and pulls in many npm dependencies, with no advantage over the release build.
- **Version pinned to 2026.8.0 (owner decision).** With 2026.10.1, login against the owner's Vaultwarden 2026.6.0 on netmaster failed after authentication: the CLI posts the user key id (`key_id_backfill`) to an endpoint Vaultwarden does not have (HTTP 404), and `machine env pull` wrote no env files. 2026.8.0 works against the same server (laptop, 2026-10-31). The fragment therefore names an exact version instead of `latest`; it is raised only after checking a newer CLI against the server. Rejected: searching for the newest working version (a login per version) and updating Vaultwarden first (unverified whether it adds the endpoint).
- **In the `core` group, every host (owner decision).** `env pull`, the SSH key backup and the SSH host list are used on every host, so `bw` is installed with the other tools and the install question is no longer needed in normal use. The fragment is `home/core/.config/mise/conf.d/20-tools.toml`.
- **Early install from the repository configuration.** When `bw` is missing, `ensure_bitwarden_cli` runs `mise install bitwarden` with `MISE_CONFIG_DIR` pointing to `<repo>/home/core/.config/mise`, so the version comes from the repository's lockfile even before `~/.config/mise` is linked. It then puts the directory from `mise where bitwarden` on `PATH` for the rest of the run (the shims directory is not yet active in this process). The later `mise install` in `run_tools_install` finds the tool already installed. `require_bitwarden` keeps its "Install it now?" question for a host where `bw` is still missing and calls the same function.
- **Old `~/.local/bin/bw` removed once (owner decision).** `machine` puts `~/.local/bin` at the front of `PATH`, so an old download there would win over the mise build. After `mise` provides `bw`, setup and update delete `~/.local/bin/bw` and log it. Only that path is touched.
- **`machine` puts the mise shims on `PATH` (owner decision).** The old `bw` lay in `~/.local/bin`, which `machine` always adds to `PATH`, also for `ssh host cmd` without a login shell. A mise tool is reachable there only through the shims directory, which `.zshenv` and `.profile` set; on a host whose login shell is bash, a plain `ssh host cmd` reads neither. `machine` therefore also prepends `~/.local/share/mise/shims` when it exists. Side effect accepted: over such an ssh call `machine` uses the mise Git too, as zsh hosts already do. Rejected: only documenting the gap, which would leave `machine` without `bw` until its own install step runs.
- **`unzip` stays a bootstrap tool only if something else needs it.** It was installed for the `bw` download; mise unpacks the release itself. Whether another caller needs `unzip` is checked during implementation; if none does, the install step is removed.
- **Completion.** `bw completion --shell zsh` generates a zsh completion; it is added to the cached tool completions in `home/core/.shell/zsh/plugins.zsh` like `gh`. `bw` offers no Bash completion, which is noted next to the Bash completion list.

## Risks / Trade-offs

- [Containers and devcontainers also download `bw` (about 30 MB zip) because the tool is in `core`] → accepted with the owner's choice of `core`. If it becomes a problem, the tool can move to a group that is selected for non-container devices only.
- [A `bw` outside `~/.local/bin` (for example `/usr/local/bin/bw` on the owner's laptop, 2026.8.0) can still come before the mise shims on `PATH`] → not removed by design; `machine` uses whatever `bw` resolves to, as today.
- [The aqua entry for `bitwarden/clients` has no checksum source for recent versions] → `mise lock` computes and stores the sha256 of each platform's asset, so installs are still verified against the lockfile.
- [A future Bitwarden release changes its asset names] → the lockfile keeps the pinned version installable; an upgrade then waits for the registry entry to be updated.
- [Mise install of `bw` fails (network)] → `ensure_bitwarden_cli` returns false and logs it; setup continues without Bitwarden as today (`Missing Influx item does not block the run`), and the old `~/.local/bin/bw` is kept.

## Migration Plan

- Existing x86_64 hosts: the next `machine update` sees the changed mise fragment and lockfile, installs `bitwarden`, then removes `~/.local/bin/bw`. A saved `BW_SESSION` and the `bw` data in `~/.config/Bitwarden CLI` stay valid, because only the binary changes.
- `netmaster` and other aarch64 hosts: the same `machine update` installs the arm64 build; `machine env pull` then works.
- Rollback: revert the commit; `machine env pull` offers the old download again on x86_64.
