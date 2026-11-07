# Proposal

## Why

On 2026-11-06 a `machine update` on ThinkPad-L13-Yoga-Gen-2 failed at the first Ansible task with "Timed out waiting for become success or become password prompt", although the owner had entered the correct sudo password at `machine`'s prompt "sudo password for Ansible".

The host uses fingerprint authentication: `/etc/pam.d/common-auth` starts with `pam_fprintd.so max-tries=3 timeout=10` (the local PAM profile `fprintd-custom-timeout`, see `docs/fingerprint.md`), so every `sudo` first waits up to 10 s for a finger before PAM asks for the password. Today `machine` runs `ansible-playbook` as the login user, and Ansible calls `sudo` again for every task that needs root and waits at most 10 s (its default timeout) for the password prompt. Ansible therefore gives up before the prompt appears. A longer Ansible timeout would only make each root task wait 10 s. A sudo ticket from `machine`'s password check does not help, because Ansible runs each `sudo` in a new pseudo-terminal.

The owner wants a local Ansible run to need one authentication in the terminal, by fingerprint or password, whatever PAM offers, and no `sudo` per task.

## What Changes

- For local runs (`machine setup`, `machine apply`, the apply step of `machine update`), `machine` first authenticates with `sudo -v` in the terminal. That prompt comes from sudo and PAM (fingerprint or password). It then runs `ansible-playbook` itself as root through `sudo`. On the owner's work hosts sudo allows every command with a password (only one command runs without a password), so the run as root works there as well. A host whose sudo refuses `ansible-playbook` as root fails with a message that names the command and `ansible: false`; there is no fallback to the per-task run (owner decision).
- `machine`'s own prompt "sudo password for Ansible" and the private password file for local runs are removed.
- Tasks that must run as the login user (the Docker and Compose checks in the packages play, the touch-device play for the GNOME session) switch from `become: false` to `become: true` with `become_user` set to the login user. `machine` passes the login user and the session variables the touch-device play needs (`DBUS_SESSION_BUS_ADDRESS`, `XDG_RUNTIME_DIR`) to Ansible. The role `sshd_home` takes the user for `authorized_keys` from that variable; its read of `machine/ssh_keys/` on the controller keeps `become: false`, which is now root and can read the checkout.
- The run as root keeps what it needs from the login user's environment: the login user's `PATH` (already passed as `machine_user_path`), the hardware override `MACHINE_HARDWARE`, the vault password file, and the location of the user's Ansible collections.
- Without a terminal (the update check job, CI), `machine` uses `sudo -n` and fails with the existing message when sudo would need authentication. When `machine` already runs as root (containers, test environments), it runs `ansible-playbook` directly.
- Remote runs (`machine apply --limit <host>`, the `homelab` playbook) are unchanged and keep `--ask-become-pass`.
- Docs: `docs/update.md` (restricted sudo: the command to request) and `docs/fingerprint.md` (Ansible asks once, fingerprint works).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `system-provisioning`: local Ansible runs authenticate once and run as root; tasks for the login user switch to it explicitly; behaviour without a terminal, as root, and on hosts with restricted sudo.
- `update-flow`: the hint after a failed Ansible apply names the command `sudo ansible-playbook` that needs administrator approval on hosts with restricted sudo.

Affected profiles: private and work desktops and servers with Ansible (every host without `ansible: false`). Containers run as root and are not affected. Remote runs are not affected.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/ansible-single-sudo`. The change touches the `machine` CLI (`machine_cli/tools.py`, `machine_cli/commands.py`) and the workstation playbook, which the host's own `machine update` runs from the live checkout.

## Impact

- `machine_cli/tools.py` (`run_ansible`, `local_become_password` removed), `machine_cli/commands.py` (failure hint).
- `ansible/workstation.yml`, `ansible/roles/sshd_home/tasks/main.yml`, `ansible/roles/sshd_home/defaults/main.yml`, the role `touch_device`.
- Tests: `tests/unit/test_host_profiles.py` (Ansible command line, password handling), tests of the playbook's login-user tasks.
- Docs: `docs/update.md`, `docs/fingerprint.md`.
