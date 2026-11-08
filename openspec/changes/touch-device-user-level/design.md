# Design

## Context

See proposal.md - Why.

Current state:

- The play "Touch device" in `ansible/workstation.yml` runs the role `touch_device` with `become: "{{ machine_runs_as_root | bool }}"`, `become_user: "{{ machine_login_user }}"` and `environment: "{{ machine_user_session_env }}"`. Its only gate is `'touch-device' in machine_features`; it uses no hardware facts from `tasks/detect_hardware.yml`. The role reads `gnome-shell --version`, downloads each missing extension from extensions.gnome.org with `curl` and runs `gnome-extensions install --force` and `gnome-extensions enable`. Every task is skipped when `machine_user_session_env` has no `DBUS_SESSION_BUS_ADDRESS`, which is the case for remote (`--limit`) runs and runs without a session.
- `machine_user_session_env` (from `SESSION_ENV` in `machine_cli/tools.py`, default `{}` in `group_vars/all/login_user.yml`) exists only for this role (archived `ansible-single-sudo` design, decision 3). `machine_login_user` and `machine_runs_as_root` are also used by the Docker checks and `sshd_home` and stay.
- For the feature `gnome`, `MiseToolsMixin.run_tools_install` (`machine_cli/mise_tools.py`) already installs and enables GNOME Shell extensions without root with `gext -F` from the `mise` group `gnome` (`pipx:gnome-extensions-cli`), skips hosts without `gnome-shell`, logs a failed install with its reason and continues, and prints "log out and in" after a new install. The step runs on `machine setup`, `machine apply` and on every `machine update` (converge step "tool install").
- The feature `touch-device` is optional on desktops and excluded on servers and in containers; it selects no dotfile group today.
- The archived `adopt-mise` design listed `touch_device` among the system roles that were not moved out of Ansible (Non-Goals) and states under Decisions that replacing "the five root roles" with `mise bootstrap` is a separate later change.
- Update flow: `system_relevance.is_relevant_path` counts every change to a playbook, and a changed file under `roles/<r>/` whose role no playbook names any more counts as well.

## Goals / Non-Goals

**Goals:**

- The touch extensions are installed and enabled by `machine` at the user level, with the same behaviour as the `gnome` extensions (idempotent, no root, failures logged and not fatal).
- Ansible no longer contains user-level work for this feature, and the plumbing that only served it is gone.
- The live documentation states the current decision about Ansible and `mise bootstrap`.

**Non-Goals:**

- Migrating root roles or the packages play to `mise bootstrap`.
- Hardware gating or detection in Python; the feature stays the only gate, as in the play.
- A new `machine` subcommand (none is needed; the memory rule "no hardware-specific CLI commands" stays satisfied).
- Removing the touch extensions from hosts that drop the feature (the role never did that either).
- Editing archived changes.

## Decisions

These are the owner's decisions of 2026-11-08 that this change carries out:

1. **Separation stays.** `mise` and `machine` handle the user level, Ansible handles root and system work. The root roles are not migrated to `mise bootstrap`.
2. **`touch_device` leaves Ansible.** Its work is user-level, so it moves to `machine`.
3. **`mise bootstrap` is re-evaluated in 6 to 12 months** (between 2027-05 and 2027-11) against these criteria: validation before a file is written (`sshd -t`, `visudo -c`), conditions per host and per fact, debconf, partial edits of files (as with `lineinfile`), a single sudo authentication per run, and a `mise` binary for the Raspberry Pi Zero.
4. **The correction lives in the live docs.** The outdated "five root roles" statement of the archived `adopt-mise` design is not edited; `docs/architecture.md` gets a decision note "Ansible stays for root work" with the role count after this change (ten local roles: nine feature roles and the model role `thinkpad_l13_yoga_gen2`, plus the packages play), the decision and the re-evaluation criteria. No live spec repeats the outdated statement, so none needs a correction for it.

## Proposed design (recommendations, not yet confirmed by the owner)

The points below are the agent's recommendations; each is also listed under Open Questions.

- **Same step and CLI as the `gnome` extensions.** A second tuple (for example `TOUCH_EXTENSIONS = ("touchup@mityax", "screen-rotate@shyzus.github.io")`) next to `GNOME_EXTENSIONS`, installed by the existing install/enable loop (factored to take a list) when `touch-device` is in the host's features. Rationale: one code path, the same `gext` that already handles shell-version selection and filesystem install, and the same tests. Alternatives: keeping the role's `curl` + `gnome-extensions install` logic in Python (duplicates what `gext` does); a `mise` task (would need its own feature gating and failure handling, which `machine` already has); a `machine touch` subcommand (not needed, and against the memory rule for hardware-specific commands).
- **Separate failure tracking.** A failed touch extension is logged and does not block the one-time `dconf load` of the `gnome` extension settings, whose marker depends only on the `gnome` extensions.
- **`touch-device` selects the group `gnome`.** The feature table gets `groups: [gnome]` for `touch-device`, so `gext` is present on a touch host without `gnome`. Groups may be shared between features (as `openspec` is). The group also links the `gnome` dconf files into `~/.config/machine/dconf`; they are only loaded when the feature `gnome` is set. Alternatives: a new group `gnome-extensions` holding only `gext`, selected by both features (cleaner, one more group to move the tool into); requiring `gnome` for `touch-device` (couples two independent features).
- **Remove `machine_user_session_env`.** `SESSION_ENV`, the extra var, its default in `group_vars/all/login_user.yml` and its assertion in `tests/unit/test_host_profiles.py` go with the role, because nothing else reads them. Alternative: keep it for future login-user tasks (dead code until then, and the new spec requirement forbids such Ansible tasks).
- **Hosts with `ansible: false` gain the touch extensions.** Today the role never runs there; after the change `machine` installs them like the `gnome` extensions. This follows from the user-level placement and needs no special handling.
- **No migration code.** The role installed into `~/.local/share/gnome-shell/extensions` as the login user, where `gext -F` installs too, so the new step finds the extensions present and only enables them. Nothing is left in `/etc` or root's home to undo.

## Risks / Trade-offs

- [One pending system step on every host that runs Ansible, because `ansible/workstation.yml` changes and the deleted role counts as relevant] → Accepted: the run is a normal `machine update` system step that changes nothing; no special case in `system_relevance` for deleted roles.
- [`gext` picks a different extension version than the role's `shell_version` download] → Both resolve the version for the installed GNOME Shell from extensions.gnome.org; already-installed extensions are not reinstalled, so existing hosts keep their version.
- [Replaying the new step outside a container writes the real session's dconf and enables extensions there] → Validate end to end with `machine testenv` or the unit tests only; a scratch `HOME` does not isolate dconf, gsettings or `gext enable`.
- [Enabling re-enables an extension the user switched off by hand] → Same behaviour as the role and as the `gnome` extensions; not changed here.

## Migration Plan

1. Land the `machine` step and the feature-table change together with the removal of the play, the role and the session-env plumbing, in one commit series on the branch.
2. On each host, the next `machine update` runs the new code: the tool-install step enables the touch extensions (already present on the L13), and the pending system step runs Ansible without the touch play.
3. Rollback: revert the branch; the next update restores the play. Nothing on the host needs undoing, because both paths install into the same user directory.

## Open Questions

1. **Reuse the `gnome` extension step and `gext`?** Recommendation: yes (see Proposed design).
2. **How does a touch host without `gnome` get `gext`?** Recommendation: `groups: [gnome]` for `touch-device`; alternative a new shared group `gnome-extensions`.
3. **Remove `machine_user_session_env` and `SESSION_ENV`?** Recommendation: remove.
4. **Accept the one no-op pending system step on every Ansible host?** Recommendation: accept, no special case in the relevance filter.
5. **Should hosts with `ansible: false` and `touch-device` get the extensions?** Recommendation: yes, it follows from the user-level placement.
6. **Where does the `mise bootstrap` re-evaluation get tracked?** Recommendation: the decision note in `docs/architecture.md` with the date window; no reminder automation.
