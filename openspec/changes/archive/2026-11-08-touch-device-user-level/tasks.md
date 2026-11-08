# Tasks

Work only in the worktree `$(machine repo)/.worktrees/touch-device-user-level`.

## 1. Owner decisions

- [x] 1.1 Ask the owner the remaining Open Questions 4 to 6 of design.md (1 to 3 are answered, Decisions 5 to 8), numbered with the recommended option marked; write the answers into design.md (move confirmed points from "Proposed design" to Decisions) and adjust the tasks below if an answer differs from the recommendation; verify with `openspec validate touch-device-user-level --strict`

## 2. Touch extensions in machine

- [x] 2.1 In `machine_cli/mise_tools.py` add the touch extension UUIDs (`touchup@mityax`, `screen-rotate@shyzus.github.io`, taken from `ansible/roles/touch_device/defaults/main.yml`) and install/enable them with `gext -F` in `run_tools_install` when `touch-device` is in the host's features, reusing the `gnome` install/enable loop; a failed touch extension is logged with its reason and does not block the `gnome` settings load; verify with the tests of 2.3
- [x] 2.2 Create the dotfile group `gnome-extensions`: move `home/gnome/.config/mise/conf.d/60-gnome.toml` to `home/gnome-extensions/.config/mise/conf.d/60-gnome-extensions.toml` (adjust its comment), add `[dotfile_groups.gnome-extensions]` to `mise.toml`, and set `groups: [gnome, gnome-extensions]` for `gnome` and `groups: [gnome-extensions]` for `touch-device` in `ansible/group_vars/all/features.yml`; add tests that a `gnome` host gets both groups and a `touch-device` host without `gnome` gets only `gnome-extensions`; verify `pytest tests/unit/test_features.py tests/unit/test_dotfiles.py -q` passes (the group test lives in `test_features.py`)
- [x] 2.3 Add unit tests in `tests/unit/test_mise_tools.py`: touch host installs and enables both extensions, second run changes nothing, already-present extensions are only enabled, host without `touch-device` or without `gnome-shell` installs none, touch install failure is logged and the `gnome` settings still load once, touch host without `gnome` does not install the `gnome` extensions, a `gnome` host still installs its extensions with `gext`; verify `pytest tests/unit/test_mise_tools.py -q` passes
- [x] 2.4 Document the touch extensions in `docs/features.md` (installed by `machine` with `gext`, log out and in) and in `docs/thinkpad-l13-yoga-gen2.md` (table row and section "Touch extensions": `machine` instead of role `touch_device`); verify by `grep -rn touch_device docs` returning nothing

## 3. Remove the Ansible role

- [x] 3.1 Delete `ansible/roles/touch_device/` and the play "Touch device (GNOME extensions for the login user)" from `ansible/workstation.yml`; remove its entry from `LOGIN_USER_TASKS` in `tests/unit/test_ansible_become.py`; verify `pytest tests/unit/test_ansible_become.py -q` passes and `grep -rn touch_device ansible` returns nothing
- [x] 3.2 Remove `machine_user_session_env`: `SESSION_ENV` and the extra var in `machine_cli/tools.py`, the default and comment in `ansible/group_vars/all/login_user.yml`, the assertion in `tests/unit/test_host_profiles.py`; verify `grep -rn -e machine_user_session_env -e SESSION_ENV machine_cli ansible tests` returns nothing and `pytest tests/unit/test_host_profiles.py -q` passes
- [x] 3.3 Update `ansible/README.md` (role table), `Readme.md` (tree), `docs/update.md` (login-user tasks are only the Docker checks); verify `grep -rn -e touch_device -e "touch-device extensions" Readme.md ansible/README.md docs` returns nothing

## 4. Decision note on Ansible and mise bootstrap

- [x] 4.1 Add a decision note "Ansible stays for root work" to `docs/architecture.md`: it replaces the "five root roles" statement of the archived `adopt-mise` design, names the count after this change (ten local roles plus the packages play), the owner's decision of 2026-11-08, the re-evaluation window (2027-05 to 2027-11) and the criteria (validation before write such as `sshd -t` / `visudo -c`, per-host and per-fact conditions, debconf, partial file edits as with `lineinfile`, a single sudo authentication, a `mise` binary for the Pi Zero); update the Ansible row of the Layers table to "root work only"; verify the role count against `ls ansible/roles`

## 5. Validation

- [x] 5.1 Run the targeted tests: `pytest tests/unit/test_mise_tools.py tests/unit/test_features.py tests/unit/test_ansible_become.py tests/unit/test_host_profiles.py tests/unit/test_system_relevance.py tests/unit/test_dotfiles.py -q` (tool step, feature groups, become rules, Ansible extra vars, relevance of the removed role, group selection); record the result
- [x] 5.2 Run `ansible-lint ansible/*.yml` (playbook and role removal) and record the result
- [x] 5.3 End-to-end check only in a container, never with a scratch `HOME` (dconf, gsettings and `gext enable` reach the real session): on the L13, run this branch's CLI inside `machine testenv` (the worktree lies under `~/dotfiles`, so it is visible there), e.g. `machine testenv -- '~/dotfiles/.worktrees/touch-device-user-level/machine_cli/machine apply'` for the Ansible part and `... machine setup --yes --skip-ansible` for the dotfile and tool steps (`machine apply` runs only Ansible); verify the runs complete, the Ansible output has no touch play, `~/.config/mise/conf.d/60-gnome.toml` is gone and `60-gnome-extensions.toml` is linked, and the tool-install step does not fail (the container may lack GNOME Shell, in which case the touch step is skipped; the extension logic itself is covered by 2.3)
- [x] 5.4 Run `pre-commit run --files <changed paths>` including the deleted and new files, and fix findings
- [x] 5.5 Run `openspec validate touch-device-user-level --strict`
- [x] 5.6 Review the branch diff against `main` with a fresh reviewer (`/review` or a review subagent), because the change touches the `machine_cli` tool-install step and a shared Ansible playbook; fix findings and rerun the affected checks of 5.1 to 5.5

## Workflow follow-up

- After merge, the next `machine update` on the L13 runs one pending system step; confirm the touch extensions stay enabled after logging in again.
- Archive the change with spec sync (`/opsx-archive`).
