# Tasks

## 1. Verify

- [x] 1.1 On ThinkPad-L13-Yoga-Gen-2, check the Assumptions in design.md: `sudo -n true` as root with `sudo.ws` and with sudo-rs; `sudo -n -l <abs ansible-playbook>` with and without a valid ticket and for a refused command (a scratch sudoers rule is not needed: use a command path outside the rules on a host with restricted sudo, or read the exit codes from `sudo(8)`); where `ansible-galaxy collection list` finds `ansible.posix` for the user; and `sudo -u $USER env DBUS_SESSION_BUS_ADDRESS=... XDG_RUNTIME_DIR=... gnome-extensions list` from a root shell. Replace the Assumptions with the verified facts and settle the collection path in decision 4.

## 2. machine CLI

- [x] 2.1 Write the tests listed under Testing in design.md for `run_ansible` in `tests/unit/test_host_profiles.py`, and adjust the existing tests that expect `--become-password-file` or the getpass prompt for local runs; verify the new ones fail.
- [x] 2.2 Implement `local_ansible_prefix` and the local path of `run_ansible` as outlined in design.md, remove `local_become_password`, and name `sudo ansible-playbook` in the failure hint in `machine_cli/commands.py`; verify `pytest tests/unit/test_host_profiles.py tests/unit/test_machine_cli.py -q` passes.

## 3. Playbook

- [x] 3.1 Write the test that only the listed tasks in `ansible/` use `become: false`; verify it fails for the Docker checks and the play "Touch device".
- [x] 3.2 Change the Docker and Compose checks and the play "Touch device" in `ansible/workstation.yml`, `ansible/roles/touch_device/tasks/main.yml` and `ansible/roles/sshd_home/defaults/main.yml` as in decision 3; verify the test of 3.1 passes and `ansible-lint ansible/*.yml` reports nothing.

## 4. Docs

- [x] 4.1 Update `docs/update.md` ("Failed apply and restricted sudo": one authentication, `sudo -n` without a terminal; rephrase the restriction in general terms, for hosts whose sudo refuses `ansible-playbook` as root, without naming managed work machines as the example, and name the command to request) and `docs/fingerprint.md` (Ansible asks once through sudo, fingerprint works).

## 5. Validation

- [x] 5.1 Run `pytest tests/unit -q`, because `run_ansible` is shared by setup, apply, update and attention. Record the result here.
  - 2026-11-07: `pytest tests/unit -q`: 1042 passed. Fixed on the way: the Docker provider fixture in `test_package_presets.py` drops `become`/`become_user` of the stubbed checks, and the telegraf helper runs as root; new test for `INFLUX_*` from the environment. One earlier run had a failure in `test_command_prefix.py` that moved between cases and passed on rerun (timing of the pty test, not touched by this change).
- [x] 5.2 Run `ansible-lint ansible/*.yml` and the Docker integration test of the CI laptop host (`tests/integration/test_host_yaml_install.py`, see `docs/testing.md`) for the as-root path. Record the results here.
  - 2026-11-07: `uvx --from 'ansible-lint>=24.2.0' ansible-lint ansible/*.yml`: 0 failures, 0 warnings (40 files); `ansible-playbook --syntax-check`: ok. `uvx nox -s docker -- -m "apt or apt_gnome" -k "sudo_password or home_laptop"`: 2 passed (6:24 min) after one fix: the first run failed on `ansible.posix` because `ANSIBLE_COLLECTIONS_PATH` replaced Ansible's default search path; it now keeps `/usr/share/ansible/collections` after the user's directory. `test_install_with_sudo_password` ran `machine setup` in a pseudo-terminal with exactly one sudo prompt; the laptop run includes the idempotency check.
- [x] 5.3 By hand on ThinkPad-L13-Yoga-Gen-2 with fingerprint PAM: `machine apply` once with the finger and once with the password after the fingerprint timeout; check that no further prompt appears and that the touch-device extensions stay enabled in the GNOME session. Record the results here.
  - 2026-11-07 on ThinkPad-L13-Yoga-Gen-2 (fingerprint PAM, `max-tries=3 timeout=10`), from the worktree with `DOTFILES_REPO=$PWD uv run --script machine_cli/machine apply`: (a) one prompt "sudo for Ansible (fingerprint or password)", then Ansible ran as root to the end, `ok=106 changed=0 failed=0`; the Docker checks and the touch-device play ran as the login user, `touchup@mityax` and `screen-rotate@shyzus.github.io` stay enabled; no root-owned files in `~/.ansible` or the uv tool. (b) Ctrl+C at the fingerprint prompt aborted `machine` ("Aborted!") although sudo had moved on to the password; fixed by ignoring SIGINT while `sudo -v` runs, with a unit test. (c) After `sudo.ws -k`: fingerprint timeout ("Zeitüberschreitung bei der Verifizierung"), password typed once, no further prompt, `ok=106 changed=0 failed=0`, "apply finished".
- [x] 5.4 Run `pre-commit run --files <changed paths>` (machine CLI, playbook, roles, tests, docs and `openspec/changes/ansible-single-sudo/**`) and record the result.
  - 2026-11-07: `pre-commit run --files` on all 21 changed and new paths: passed after black reformatted `tests/integration/test_host_yaml_install.py`, a German prompt quote in design.md was rephrased (codespell) and a slice in `test_host_profiles.py` was split (flake8 E203).
- [x] 5.5 Run `openspec validate ansible-single-sudo --strict` and record the result.
  - 2026-11-07: `openspec validate ansible-single-sudo --strict`: valid.
- [x] 5.6 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change touches the `machine` CLI core, shared Ansible plays and roles, and needed escalated validation; fix findings before archive.
  - 2026-11-07: review by a fresh subagent of `15bfa23` against `origin/main`. Fixed: (1) a failed sudo check stopped with `SystemExit`, so `cmd_apply` did not restore the host config (spec `update-flow`); it now raises `CalledProcessError` for the sudo command like a failed Ansible run; (2) `--no-become` in a terminal named the wrong remedy; (3) `PYTHONDONTWRITEBYTECODE=1` for the root run, so no root-owned `__pycache__` lands in the user's home; (4) an expired ticket after `sudo -v` is no longer reported as a refusal; (6) the login-user tasks become the login user only when `machine_runs_as_root` is passed, so remote runs are unchanged; (7) tests for the messages, `--no-become` without a ticket, and nameless blocks in the `become: false` guard. (5) sudo-rs without `sudo.ws` is recorded under Assumptions. After the fixes: `pytest tests/unit -q` 1044 passed; ansible-lint 0 failures; Docker `sudo_password` and `home_laptop` 2 passed (6:02 min); pre-commit and `openspec validate --strict` passed.
