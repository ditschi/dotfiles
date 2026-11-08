# Tasks

Work only in the worktree `$(machine repo)/.worktrees/touch-device-user-level`.

## 1. Owner decisions

- [ ] 1.1 Ask the owner the Open Questions of design.md (ask_user form, recommended option as default); write the answers into design.md (move confirmed points from "Proposed design" to Decisions) and adjust the tasks below if an answer differs from the recommendation; verify with `openspec validate touch-device-user-level --strict`

## 2. Touch extensions in machine

- [ ] 2.1 In `machine_cli/mise_tools.py` add the touch extension UUIDs (`touchup@mityax`, `screen-rotate@shyzus.github.io`, taken from `ansible/roles/touch_device/defaults/main.yml`) and install/enable them with `gext -F` in `run_tools_install` when `touch-device` is in the host's features, reusing the `gnome` install/enable loop; a failed touch extension is logged with its reason and does not block the `gnome` settings load; verify with the tests of 2.3
- [ ] 2.2 Give `touch-device` `groups: [gnome]` in `ansible/group_vars/all/features.yml` (or the group chosen in 1.1); verify `pytest tests/unit/test_features.py -q` passes and a host with `touch-device` without `gnome` gets the group
- [ ] 2.3 Add unit tests in `tests/unit/test_mise_tools.py`: touch host installs and enables both extensions, second run changes nothing, already-present extensions are only enabled, host without `touch-device` or without `gnome-shell` installs none, touch install failure is logged and the `gnome` settings still load once, touch host without `gnome` does not install the `gnome` extensions; verify `pytest tests/unit/test_mise_tools.py -q` passes
- [ ] 2.4 Document the touch extensions in `docs/features.md` (installed by `machine` with `gext`, log out and in) and in `docs/thinkpad-l13-yoga-gen2.md` (table row and section "Touch extensions": `machine` instead of role `touch_device`); verify by `grep -rn touch_device docs` returning nothing

## 3. Remove the Ansible role

- [ ] 3.1 Delete `ansible/roles/touch_device/` and the play "Touch device (GNOME extensions for the login user)" from `ansible/workstation.yml`; remove its entry from `LOGIN_USER_TASKS` in `tests/unit/test_ansible_become.py`; verify `pytest tests/unit/test_ansible_become.py -q` passes and `grep -rn touch_device ansible` returns nothing
- [ ] 3.2 Remove `machine_user_session_env`: `SESSION_ENV` and the extra var in `machine_cli/tools.py`, the default and comment in `ansible/group_vars/all/login_user.yml`, the assertion in `tests/unit/test_host_profiles.py` (unless 1.1 decided to keep it); verify `grep -rn -e machine_user_session_env -e SESSION_ENV machine_cli ansible tests` returns nothing and `pytest tests/unit/test_host_profiles.py -q` passes
- [ ] 3.3 Update `ansible/README.md` (role table), `Readme.md` (tree), `docs/update.md` (login-user tasks are only the Docker checks); verify `grep -rn -e touch_device -e "touch-device extensions" Readme.md ansible/README.md docs` returns nothing

## 4. Decision note on Ansible and mise bootstrap

- [ ] 4.1 Add a decision note "Ansible stays for root work" to `docs/architecture.md`: it replaces the "five root roles" statement of the archived `adopt-mise` design, names the count after this change (ten local roles plus the packages play), the owner's decision of 2026-11-08, the re-evaluation window (2027-05 to 2027-11) and the criteria (validation before write such as `sshd -t` / `visudo -c`, per-host and per-fact conditions, debconf, partial file edits as with `lineinfile`, a single sudo authentication, a `mise` binary for the Pi Zero); update the Ansible row of the Layers table to "root work only"; verify the role count against `ls ansible/roles`

## 5. Validation

- [ ] 5.1 Run the targeted tests: `pytest tests/unit/test_mise_tools.py tests/unit/test_features.py tests/unit/test_ansible_become.py tests/unit/test_host_profiles.py tests/unit/test_system_relevance.py tests/unit/test_dotfiles.py -q` (tool step, feature groups, become rules, Ansible extra vars, relevance of the removed role, group selection); record the result
- [ ] 5.2 Run `ansible-lint ansible/*.yml` (playbook and role removal) and record the result
- [ ] 5.3 End-to-end check only in a container, never with a scratch `HOME` (dconf, gsettings and `gext enable` reach the real session): on the L13, run this branch's CLI inside `machine testenv` (the worktree lies under `~/dotfiles`, so it is visible there), e.g. `machine testenv -- '~/dotfiles/.worktrees/touch-device-user-level/machine_cli/machine apply'`; verify the run completes, the Ansible output has no touch play, and the tool-install step does not fail (the container may lack GNOME Shell, in which case the touch step is skipped; the extension logic itself is covered by 2.3)
- [ ] 5.4 Run `pre-commit run --files <changed paths>` including the deleted and new files, and fix findings
- [ ] 5.5 Run `openspec validate touch-device-user-level --strict`
- [ ] 5.6 Review the branch diff against `main` with a fresh reviewer (`/review` or a review subagent), because the change touches the `machine_cli` tool-install step and a shared Ansible playbook; fix findings and rerun the affected checks of 5.1 to 5.5

## Workflow follow-up

- After merge, the next `machine update` on the L13 runs one pending system step; confirm the touch extensions stay enabled after logging in again.
- Archive the change with spec sync (`/opsx-archive`).
