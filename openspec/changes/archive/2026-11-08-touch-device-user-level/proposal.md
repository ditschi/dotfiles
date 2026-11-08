# Proposal

## Why

On 2026-11-08 the owner accepted the result of the analysis "replace Ansible with `mise bootstrap`?": the separation stays, with `mise` and `machine` for the user level and Ansible for root and system work, and the root roles are not migrated to `mise bootstrap`. Two follow-ups come from that decision.

The role `touch_device` does no root work: it installs and enables two GNOME Shell extensions as the login user through that user's session. Under the decision "Ansible keeps only root work" (recorded in the archived `adopt-mise` design) it belongs to the user level, next to the GNOME extensions that `machine` already installs for the feature `gnome`.

The archived `adopt-mise` design still says that replacing "the five root roles" with `mise bootstrap` is a separate later change. That is outdated: there are more roles today, and the owner decided to keep Ansible for root work and to re-evaluate `mise bootstrap` later against named criteria. Archived changes are not edited, so the current decision has to live in the live documentation.

## What Changes

- `machine` installs and enables the touch extensions (TouchUp, Screen Rotate) for hosts with the feature `touch-device`, without root, in the same tool-install step and with the same `gext` CLI from `mise` that installs the `gnome` extensions. It runs on `machine setup` and every `machine update` (also the automatic one), as the `gnome` extensions do; `machine apply` runs only Ansible and does not run it.
- A new dotfile group `gnome-extensions` holds only `gext` (moved out of the group `gnome`) and is selected by the features `gnome` and `touch-device`, so `gext` is installed on a host with `touch-device` even without the feature `gnome`, without the rest of the `gnome` group.
- The Ansible role `touch_device` and its play in `ansible/workstation.yml` are removed. The GNOME session variables that `machine` passes to Ansible only for that role (`machine_user_session_env`) are removed with it.
- No new `machine` subcommand; the step stays gated only by the feature, as today (the play used no hardware facts).
- Existing hosts need no undo: the extensions already live in the user's extension directory, where the new step finds them and only enables them.
- `docs/architecture.md` gets a decision note "Ansible stays for root work" that replaces the outdated "five root roles" statement: today's role count, the owner's decision, and the criteria for re-evaluating `mise bootstrap` in 6 to 12 months. The role tables and docs that name `touch_device` are updated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `user-tools`: new requirement for the touch extensions of the feature `touch-device`, installed by `machine` without root.
- `system-provisioning`: the local-roles requirement no longer names `touch_device` and states that local roles need root; the login-user requirement drops the GNOME touch-device session tasks.
- `repo-layout`: the layered-responsibilities requirement states that work for the login user that needs no root is done by `machine` and `mise`, not Ansible.

Affected profiles: desktops (private and work) whose host config selects `touch-device` (today the ThinkPad L13 Yoga Gen 2 and the CI host `ci-home-laptop`). Servers and containers are unaffected; the feature table excludes `touch-device` there.

## Impact

- Code: `machine_cli/mise_tools.py` (touch extensions next to `GNOME_EXTENSIONS`), `machine_cli/tools.py` (`SESSION_ENV` and the `machine_user_session_env` extra var removed), `ansible/group_vars/all/features.yml` (`groups: [gnome, gnome-extensions]` for `gnome`, `groups: [gnome-extensions]` for `touch-device`), `mise.toml` (`[dotfile_groups.gnome-extensions]`), `home/gnome/.config/mise/conf.d/60-gnome.toml` moved to `home/gnome-extensions/.config/mise/conf.d/60-gnome-extensions.toml`, `ansible/group_vars/all/login_user.yml`, `ansible/workstation.yml`; `ansible/roles/touch_device/` deleted.
- Tests: `tests/unit/test_mise_tools.py`, `tests/unit/test_host_profiles.py`, `tests/unit/test_features.py` (group selection).
- Docs: `docs/architecture.md`, `docs/features.md`, `docs/update.md`, `docs/thinkpad-l13-yoga-gen2.md`, `ansible/README.md`, `Readme.md`.
- Update flow: the removed play and role are changes under `ansible/` that count for every host that runs Ansible, so each such host gets one pending system step after this change; that run changes nothing on the system.
- Where: the worktree `$(machine repo)/.worktrees/touch-device-user-level`, because the change edits `machine_cli/` and `ansible/`, which affect the host's tools on the next `machine` run.
