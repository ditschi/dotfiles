# Tasks

## 1. Callable sudo step

- [x] 1.1 Add tests first in `tests/unit/test_host_profiles.py` for the extracted step (installed check, `sudo -n true`, `sudo -v` only in a terminal, `sudo -n -l <ansible-playbook>`, messages unchanged, root skips it) and for the cause of a failed `sudo -v`: stderr with `incorrect password attempt` gives the wrong-password message, `may not run sudo` and `not in the sudoers file` give the no-permission message, anything else the generic one, and the prompt stays on the terminal; verify they fail before 1.2
- [x] 1.2 In `machine_cli/tools.py`, move the sudo checks of `local_ansible_prefix` into one method that raises `CalledProcessError` as today, with `LC_ALL=C` and stderr read for the cause; `local_ansible_prefix` calls it, so the check before Ansible renews an expired ticket; verify with `pytest tests/unit/test_host_profiles.py -q`
- [x] 1.3 Check the three stderr texts against the real `sudo` (and `sudo-rs` where installed) with a wrong password and as a user without sudo rights, in a throwaway container or VM; adjust the patterns and record the texts in design.md

## 2. machine update

- [x] 2.1 Add tests first in `tests/unit/test_update_and_env.py`: with a system change or host-config change or `--system` the sudo step runs before `env pull`; a home-only update, `ansible: false` and `--skip-ansible` never run it; a failing sudo step skips Ansible, still runs the other steps and the summary names the failed step `ansible apply`; the automatic update never calls it; verify they fail before 2.2
- [x] 2.2 In `_update_steps` in `machine_cli/updates.py`, compute the condition for running Ansible once, call the sudo step before `env pull` when it holds, record a failure as the failed step `ansible apply` with the reason logged at once and skip Ansible at the end; verify with `pytest tests/unit/test_update_and_env.py -q`

## 3. machine apply

- [x] 3.1 Add tests first in `tests/unit/test_host_profiles.py` that `cmd_apply` runs the sudo step before `ensure_bootstrap_tools`, never with `ansible: false` or `--skip-ansible`, and restores the host config when the step fails; verify they fail before 3.2
- [x] 3.2 In `cmd_apply` in `machine_cli/commands.py`, call the sudo step before `ensure_bootstrap_tools` inside the existing `try`; verify with `pytest tests/unit/test_host_profiles.py -q`

## 4. Docs and verification

- [x] 4.1 Update `docs/update.md`: sudo is authenticated once at the start of `update` and `apply` when Ansible will run, and again right before Ansible only when the ticket expired; verify the text matches the implemented messages
- [x] 4.2 Run `pytest tests/unit -q`, because the change touches `machine_cli` core and the update flow; record the result
- [x] 4.3 Run `pre-commit run --files <changed paths>` (including untracked files) and fix findings
- [x] 4.4 Run `openspec validate early-sudo-authentication --strict`
- [x] 4.5 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change touches the `machine` update flow; fix findings before archive

## Workflow follow-up

- Archive the change with spec sync (`/opsx-archive`) in the worktree after the review.
