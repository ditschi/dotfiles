# Design

## Context

Today one value, the profile, drives everything host-specific (observed in the code):
- `machine_cli/core.py`: `PROFILES`, `FEATURE_HELP`, `ENV_GROUPS` (per profile, including `server` and `iot`), `SSH_CLASS`.
- `machine_cli/profile.py`: default profile (Docker, `MACHINE_PROFILE_OVERRIDE`, saved, inherited `MACHINE_PROFILE`, company user ID), feature defaults from `ansible/profiles/<profile>.yml`, the feature menu.
- `machine_cli/dotfiles.py`: dotfile groups (`systemd` except container, `work` for `work-machine`), Git identity and `safe.directory`, GitHub token variable, SSH remote switch.
- Ansible: `resolve_packages.yml` (slim set for `rpi-zero`, host packages except `rpi-zero`/`container`, work packages for `work-machine`), `monitoring_by_profile`, and `profile not in [...]` gates for `monitoring` and `sshd_home` in `workstation.yml`.
- Shell: `machine-profile.sh` exports `MACHINE_PROFILE` and `WORK_SETUP`; nothing else in the dotfiles reads `MACHINE_PROFILE`.
- `machine` passes the local copy `~/.config/machine/profile.yml` to Ansible as `--extra-vars`, so `profile` and `features` are extra vars with the highest precedence. The local copy is also what a failed apply restores, what `machine-profile.sh` reads at shell start, and the profile of containers and hosts without a repository file.
- The features `starship`, `yazi`, `gh-cli`, `claude-code` and `copilot-cli` are read by no code: their tools come from the `core` group on every host (`10-shell.toml`, `20-tools.toml`, `30-llm.toml`). Only `fonts` and `thunderbird` select a dotfile group, by fixed rules in `dotfiles.py`.
- The user-tools check allows each tool in only one group.
- The no-root path is implicit: per-call `--skip-ansible` / `--no-become`, and the update reports no system update for a host that never ran Ansible.
- Bitwarden holds only `env/groups/work` and `env/hosts/LR-C-0042H` (checked by the owner).

See proposal.md for the motivation and the specs for the required behaviour.

## Goals / Non-Goals

**Goals:**
- Two chosen values (context, device) and detected hardware replace the six profiles everywhere.
- One table is the single source of feature help, defaults and exclusions, for `machine` and Ansible.
- Every existing host keeps its features through the migration, apart from features its new context or device excludes and the removed no-op features.
- A new feature needs only a table row plus Ansible (packages or a role) or plus a dotfile group; the CLI is touched only for context-dependent behaviour.

**Non-Goals:**
- Laptop tuning and model roles (`split-laptop-tuning`, reworked afterwards).
- The `zram-swap` feature; it gets its table row in `split-laptop-tuning`.
- Changing the sshd port (separate change).

## Decisions

- **Three levels (owner decision).** Context `private`/`work` on top, device below it, hardware model at the bottom. The context selects dotfile behaviour and work roles; the device selects what needs a graphical session; hardware facts are detected. A new profile per combination (`work-laptop`, `work-vm`, `home-desktop`, …) was considered and not taken, because the number of profiles grows with every combination.
- **Device `desktop`/`server` (owner decision).** The axis means "graphical session or not". `server` hosts keep the full terminal setup (Starship, gh, yazi). Names considered and not taken: `headless`, `graphical`/`terminal`, `workstation`/`server`, `gui`/`cli`.
- **Container as a third device without context (owner decision).** `machine` sets it itself in Docker as today; overrides can set a context and device for the testenv. A context value `none` was considered and not taken.
- **The stricter value wins (owner decision).** Each feature has, per context and per device, preselected, optional or excluded; the result is the stricter of the two. "Active wins" was considered and rejected, because `docker` would then be preselected on work desktops, where the company installs Docker.
- **"Host config" instead of "host profile" (owner decision).** With the profile gone, the old term would mislead. `machine/hosts/<hostname>.yml` is the host config; the local file is the applied host config. "Host file" was considered and not taken.
- **Applied host config in the state directory.** The local copy is state, not configuration: it records what was last applied. It moves from `~/.config/machine/profile.yml` to `~/.local/share/machine/applied-host.yml`, next to `events.jsonl`, and is taken over once from the old file. A git-ignored file next to the host config in the repository was considered: it would cover the restore, but project containers and `sdx` mount the checkout and would write files for container host names into it, and the shell would have to find the checkout at start.
- **Dotfile groups from the table (owner decision).** Each feature lists the groups it selects; `dotfiles.py` reads them instead of fixed rules. `core` and `prompt` stay always on, `systemd` follows the device, `work` the context.
- **No-op features removed or made real (owner decision).** `starship`, `yazi` and `gh-cli` are removed; their tools stay in `core` with `uv` (owner: wanted everywhere). `claude-code`, `copilot-cli` and the new `opencode` get the groups `claude`, `copilot`, `opencode`.
- **OpenSpec through a shared group (owner decision).** Each LLM feature also lists the group `openspec`, so OpenSpec is declared once and installed with any LLM CLI. Allowing the same tool in several groups was considered; the one-group rule stays because it prevents two fragments from asking for different versions. A separate dependency mechanism between features is not needed.
- **Feature table in Ansible group vars.** `ansible/group_vars/all.yml` becomes a directory `ansible/group_vars/all/` with the package tables and a new `features.yml` holding the table (help text, groups and the five values per feature). Ansible loads it for every play; `machine` reads the same file. `ansible/profiles/` and `FEATURE_HELP` in `core.py` are removed. A separate top-level file was considered; it would need a `vars_files` line in every play.
- **Ansible uses filtered features.** Because `features` is an extra var and cannot be overridden, the group vars define `machine_features`: the host's `features` without the ones the table excludes for `context` and `device`. Every `when` uses `machine_features`; the `profile not in [...]` gates go away because the table excludes those features. `system_relevance.py` learns the new variable name.
- **Hardware facts in one task file.** `ansible/tasks/detect_hardware.yml`, included by the plays that need it, sets `hw_laptop` (`ansible_form_factor` in the portable values and a battery under `/sys/class/power_supply` with `type=Battery` and `scope` not `Device`), `hw_pi` and `hw_pi_zero` (from `/proc/device-tree/model`). It skips everything when the device is `container`.
- **CI host configs apart from the real hosts (owner request).** The CI host configs move from `machine/hosts/` to `tests/hosts/`; the test containers set `MACHINE_HOSTS_DIR=tests/hosts`, so `machine` reads them there, and `machine/hosts/` holds only real hosts. The template `_example-thinkpad-copy.yml` is removed (owner decision): `machine setup` writes the host config of a new host itself, so a template is not needed.
- **Docker packages found with dpkg-query.** The Docker preservation step read installed packages with `package_facts`, which needs apt bindings that the Ansible installed with uv does not have; it failed as soon as private hosts preselected `docker`. It now asks `dpkg-query` directly.
- **Hardware override for tests.** Docker shows Ansible no battery and no device tree, so the CI containers that stand for the L13 Yoga and the Pi Zero set `MACHINE_HARDWARE` (`laptop`, `pi`, `pi-zero`), which replaces the detection. It is an environment variable of the run, not a key of the host config, so the host config still never names hardware.
- **Docker only where installable.** Before installing, Ansible checks the apt candidate of `docker.io`; without one it removes Docker from the package list and prints a message. The owner wants both Pi Zero variants supported.
- **Default device from the boot target.** `systemctl get-default` returning `graphical.target` suggests `desktop`, otherwise `server`; the user confirms it in setup.
- **Bitwarden groups by context (owner decision).** `private` → `env/groups/private`, `work` → `env/groups/work`, container → none. The `server` and `iot` groups are dropped; no such items exist.
- **`ansible: false` instead of the implicit no-root fallback (owner decision).** Root is assumed on every host. The owner expected an explicit host setting and keeps the per-call options. The constraint "work machines may not allow Ansible to become root" in `openspec/config.yaml` is reworded accordingly.
- **Names (owner decision).** `--context`, `--device`, `MACHINE_CONTEXT`, `MACHINE_DEVICE`, `MACHINE_CONTEXT_OVERRIDE`, `MACHINE_DEVICE_OVERRIDE`; `--profile`, `MACHINE_PROFILE`, `MACHINE_PROFILE_OVERRIDE` are removed. `WORK_SETUP` stays.
- **Migration (owner decision).** The repository host configs are rewritten in this change; `machine` takes over an old `~/.config/machine/profile.yml` once and maps its `profile:` key. Mapping: `work-machine` → work/desktop, `home-laptop` → private/desktop, `home-server`/`rpi`/`rpi-zero` → private/server, `container` → container.
- **Excluded features are kept out, not refused (owner decision).** `machine` warns, Ansible ignores them through `machine_features`, and the next write drops them. Aborting until the file is fixed was considered and not taken.

## Risks / Trade-offs

- [A host updates its checkout before its host config is migrated] → both land in the same commit; the takeover maps an older local file.
- [Scripts outside the repository read `MACHINE_PROFILE`] → none known in the repository; the owner chose not to keep it.
- [Wrong laptop detection on unusual hardware] → only the Telegraf fragment depends on it in this change; it is visible in the apply output.
- [Feature defaults change for new hosts] → existing hosts keep their explicit lists; only features excluded for their context or device are dropped, which matches today's gates except for `syncthing` on servers.
- [CI matrix and integration tests are keyed by profile] → they are rewritten to context and device in this change.

## Migration Plan

1. Implement the table, the CLI and the Ansible changes; rewrite the host configs and the CI host configs in the same commit.
2. On each host, `machine update` brings the new code and its host config; the notice shows the new context and device.
3. Rollback: revert the commit; the revert restores the old host configs; the old code does not read `applied-host.yml`, so `machine setup` has to write `~/.config/machine/profile.yml` again once.

## Confirmed details

- `opencode` is optional everywhere and never preselected (owner decision).
- Containers: `zsh-full` preselected; `claude-code`, `copilot-cli` and `opencode` optional; everything that needs Ansible excluded, since Ansible does not run there.
- A private desktop without battery gets only the base Telegraf fragment.
- `netmaster` (Pi) and `homeserver` get the device `server`; `ci-home-laptop` is the CI host config that mirrors the L13 Yoga (private/desktop) and sets the device by override inside its test container.
