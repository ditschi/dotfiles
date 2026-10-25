# Proposal

## Why

The six machine profiles mix two independent questions: whether a host is private or for work, and what kind of device it is. `work-machine` covers both a laptop and a virtual machine, and a private desktop PC or a second laptop has no clean place. The owner wants three levels instead: on top the choice private or work, below it the device type, and below that whatever depends on the hardware model. From these levels most features can be preselected, and the feature menu shall only offer features that make sense for the host. Adding a new feature shall need as few places as possible.

## What Changes

- **BREAKING** The profile (`work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`) is replaced by two chosen values in the host config `machine/hosts/<hostname>.yml`:
  - `context`: `private` or `work`. It selects the behaviour of the dotfiles (Bitwarden group, Git identity, CA bundle, work dotfile group, SSH key class, GitHub token variable, `WORK_SETUP`) and enables the work roles.
  - `device`: `desktop` (graphical session: laptops, the work VM) or `server` (no graphical session, same terminal setup). `container` is a third value that `machine` sets itself inside Docker; a container has no context unless an override sets one.
- The term "host profile" becomes "host config". The local copy `~/.config/machine/profile.yml` becomes the applied host config in the `machine` state directory (`~/.local/share/machine/applied-host.yml`); it is taken over once from the old file.
- Hardware that Ansible detects is never chosen: laptop, Raspberry Pi and Pi Zero. The Pi Zero keeps the slim package set, Docker is only installed where the architecture has a package, and the Telegraf fragment follows the detected hardware. Model-specific tuning follows in `split-laptop-tuning`.
- One feature table states, for each feature, its help text, the dotfile groups it selects, and per context and device whether it is preselected, optional or excluded; the stricter value wins. The menu shows only features that are not excluded. `machine` selects dotfile groups from the table, so a new feature with its own group needs no CLI code.
- A feature in a host config that is excluded for its context or device, or no longer exists, is reported by `machine`, not applied by Ansible, and dropped the next time the file is written.
- `starship`, `yazi` and `gh-cli` stop being features; they had no effect and their tools stay in the `core` group on every host, containers included, together with `uv`. `claude-code`, `copilot-cli` and the new feature `opencode` become real features with their own groups; each also selects the group `openspec`. Today all LLM tools are installed everywhere regardless of the features.
- Bitwarden environment groups are only `private` or `work`; the groups `server` and `iot` are dropped (no such items exist in the vault).
- A host-config setting `ansible: false` skips Ansible in `setup`, `apply` and `update`. It replaces the implicit "work machine without root" fallback; `--skip-ansible` and `--no-become` stay for single runs.
- Names: `--context` and `--device` replace `--profile`; the shell exports `MACHINE_CONTEXT` and `MACHINE_DEVICE` instead of `MACHINE_PROFILE`; `MACHINE_CONTEXT_OVERRIDE` and `MACHINE_DEVICE_OVERRIDE` replace `MACHINE_PROFILE_OVERRIDE`. `WORK_SETUP` stays. The project container launcher and `machine testenv` use the new options.
- All host configs in the repository are rewritten in this change. The CI host configs move to `tests/hosts/` and the template `_example-thinkpad-copy.yml` is removed.
- Default changes for new hosts: `copilot-cli` is optional, never preselected, on private hosts; `syncthing` is preselected on private desktops and no longer offered on servers or at work.

## Capabilities

### New Capabilities
- `feature-selection`: the feature table (groups; preselected, optional, excluded per context and device), how defaults, menu and dotfile groups are derived from it, and how excluded features in a host config are handled.
- `hardware-detection`: which hardware facts Ansible detects (laptop, Raspberry Pi, Pi Zero) and what follows from them without a choice.

### Modified Capabilities
- `machine-profiles`: context and device replace the profile; host config and applied host config; defaults on setup; values exported to the shell; takeover of the old local file; `ansible: false`.
- `system-provisioning`: LLM CLIs and OpenSpec only with their features; etckeeper defaults per device; `ansible: false` replaces the no-root fallback.
- `user-tools`: what `core` installs on every host; LLM tools and OpenSpec in feature groups.
- `work-private-separation`: work detection, work group and separation based on the context; only the `private` and `work` Bitwarden groups.
- `git-config`: identity, `safe.directory`, GitHub token variable and SSH remote based on the context and device.
- `ssh-host-keys`: key class from the context.
- `update-flow`: host config instead of host profile; `ansible: false` hosts report no system update.
- `project-containers`, `home-testenv`: the container device and the new options.
- `repo-layout`, `shell-prompt`, `machine-events`, `tests-and-ci`: wording and scenarios without the removed profiles.

Affected hosts: all. Their host configs are rewritten: L13 Yoga, the T470 template and `ci-home-laptop` private/desktop; `LR-C-0042H` and `ABTVL421` work/desktop; `homeserver`, `netmaster` and `ci-rpi-zero` private/server; `ci-container` container.

## Impact

- `machine_cli`: `core.py` (`PROFILES`, `FEATURE_HELP`, `ENV_GROUPS`, `SSH_CLASS`), `profile.py`, `commands.py`, `dotfiles.py`, `mise_tools.py`, `env_pull.py`, `testenv.py`, `events.py`, `system_relevance.py`, `machine` (CLI options).
- Dotfile groups: `home/core/.config/mise/conf.d/30-llm.toml` split into new groups `claude`, `copilot`, `opencode`, `openspec` (declared in `mise.toml`); `uv` moves from `40-azure.toml` to a general `core` fragment.
- Ansible: `ansible/profiles/` replaced by the feature table; `group_vars`, `tasks/resolve_packages.yml`, `tasks/resolve_monitoring.yml`, every `when` on `features` or `profile`; new hardware detection tasks.
- Shell: `home/core/.zsh/machine-profile.sh`; launcher `home/core/.local/bin/sde`; `bootstrap`.
- Host configs under `machine/hosts/`, `machine/hosts/README.md`, `openspec/config.yaml` (the no-root constraint), Readme, `ansible/README.md`.
- Tests: unit tests for profiles, packages, CLI, env, gitconfig, testenv, relevance, mise tools; integration tests and the CI matrix in `.github/workflows/verify.yml`.
- `split-laptop-tuning` is reworked afterwards to build on the device type and hardware detection.
