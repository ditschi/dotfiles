# Design

## Context

See proposal.md for the failure and specs/ for the required behaviour.

Current state:

- `machine_cli/tools.py` `run_ansible` builds the `ansible-playbook` command. For a local run (`force_local` or no `--limit`) it adds `--connection local --limit localhost`, `target_hosts=localhost`, `machine_user_path` (the login user's `PATH`) and, when `sudo.ws` exists, `ansible_become_exe=sudo.ws` (sudo-rs wraps its prompt in a way Ansible's become plugin does not recognise). In a terminal it asks "sudo password for Ansible" (`local_become_password`: three tries, checked with `sudo -S -k -v`, cached for the command) and passes the password in a private file with `--become-password-file`. Remote runs use `--ask-become-pass`; the `homelab` playbook never gets a become prompt from `machine`.
- `ask_become` is false with `--no-become`, in containers (`cmd_setup`), and without a terminal (no prompt is possible). `machine update`'s apply step and `machine attention` call the apply with `no_become=False`.
- `ansible/ansible.cfg` sets `become = False`; every play of `ansible/workstation.yml` sets `become` itself. Plays and tasks with `become: false`: the Docker and Compose checks in the packages play (with `PATH` from `machine_user_path`), the play "Touch device" (role `touch_device`, which talks to the GNOME session through `gnome-extensions` and is skipped when the facts have no `DBUS_SESSION_BUS_ADDRESS`), and the `stat` of `machine/ssh_keys/*.pub` in `sshd_home`, delegated to localhost. `sshd_home_authorized_keys_user` is derived from the facts' `user_id` or `SUDO_USER`.
- Environment lookups on the controller: `MACHINE_HARDWARE` (`tasks/detect_hardware.yml`), the `INFLUX_*` variables (`group_vars/all/packages.yml`; `machine` passes the token in an extra-vars file instead), and `ANSIBLE_VAULT_PASSWORD_FILE` (set by `machine` for the inventory with remote hosts).
- `ansible-playbook` is a uv tool in the user's home (`~/.local/bin/ansible-playbook` → `~/.local/share/uv/tools/ansible-core`). The only collection, `ansible.posix`, is installed for the user.
- `docs/update.md` "Failed apply and restricted sudo" explains that managed work machines may allow only specific sudo commands and points to `ansible: false`. On the owner's work hosts sudo allows every command with a password; only one command runs without a password.

## Goals / Non-Goals

**Goals:**
- One authentication per local `machine` command, through sudo's own prompt, so fingerprint authentication works and no Ansible timeout can be hit.
- The playbook behaves the same as before for root tasks and for login-user tasks.

**Non-Goals:**
- Changing the fingerprint PAM setup (`docs/fingerprint.md` stays a manual setup).
- Remote runs and the `homelab` playbook.
- A fallback to per-task become on hosts with restricted sudo (owner decision).

## Decisions

1. **`ansible-playbook` runs as root for local runs.** `machine` runs `sudo -v` in the terminal (skipped when `sudo -n true` already works), then `sudo -- env <vars> <absolute path of ansible-playbook> ...`. The plays keep `become: true`. As root, Ansible's become to root does not authenticate. Running through `env` passes the needed variables without needing sudo's `SETENV` permission. Rejected by the owner: a longer Ansible timeout (every root task would still wait 10 s for a finger), keeping `machine`'s own password prompt with `sudo -S` (the fingerprint would never be offered), and `timestamp_type=global` in sudoers (any process of the user could use sudo without asking for the ticket's lifetime).
2. **Sudo asks, not `machine`.** `machine` no longer reads the password. `sudo -v` uses the terminal and PAM, so the user gets the fingerprint prompt or the password prompt as configured. A revert run in the same command uses the same ticket of the terminal. `local_become_password`, the private password file and `--become-password-file` are removed for local runs.
3. **Login-user tasks switch to the login user explicitly.** `machine` passes `machine_login_user` (the user who started `machine`) and `machine_user_session_env` (`DBUS_SESSION_BUS_ADDRESS` and `XDG_RUNTIME_DIR` when set) as extra vars. The Docker and Compose checks and the play "Touch device" use `become: "{{ machine_runs_as_root | bool }}"` with `become_user: "{{ machine_login_user }}"`. `machine` passes `machine_runs_as_root: true` for local runs; it defaults to false in `group_vars/all/login_user.yml`, so remote runs keep running these tasks as the connecting user without becoming anyone, as before. The touch-device tasks get `environment: "{{ machine_user_session_env }}"` and are skipped when it has no `DBUS_SESSION_BUS_ADDRESS`. `sshd_home_authorized_keys_user` defaults to `machine_login_user`, with the old fact-based value as fallback for remote runs. The `stat` of the key files on the controller keeps `become: false`, which runs as root and can read the checkout. A separate playbook for user tasks was rejected by the owner (two Ansible runs, more moving parts).
4. **The environment of the root run is explicit.** `env` gets `MACHINE_HARDWARE` and `ANSIBLE_VAULT_PASSWORD_FILE` when set, and `ANSIBLE_COLLECTIONS_PATH`: the user's value when set, else Ansible's default search path with the user's directory in place of root's (`~/.ansible/collections:/usr/share/ansible/collections`), so collections installed system-wide (as in the test containers) are found as well. `ansible-galaxy collection list` finds `ansible.posix` for the user on ThinkPad-L13-Yoga-Gen-2. `HOME` is root's (sudo's default), so Ansible's own temporary files stay in root's home. `PYTHONDONTWRITEBYTECODE=1` keeps Python from writing root-owned `__pycache__` into the user's uv tool or collections, which would break a later `uv tool upgrade` as the user, so nothing root-owned appears in the user's home. `cwd` stays `ansible/`, so `ansible.cfg` is read as before.
5. **No terminal, `--no-become`, or already root; failures count as a failed Ansible run.** A failed sudo check (sudo missing, no ticket without a terminal, failed `sudo -v`, refused or expired `sudo -n -l`) logs its reason and raises `CalledProcessError` for that sudo command, like a failed `ansible-playbook`, so `machine apply` and the apply step of `machine update` restore the host config as the spec `update-flow` requires, and setup reports the step as failed. Without a terminal or with `--no-become`, `machine` skips `sudo -v` and runs `sudo -n -- env ... ansible-playbook`, so a host with passwordless sudo or a valid ticket still works and any other host fails at once instead of waiting. When `machine` runs as root (containers, test environments), it runs `ansible-playbook` directly with the same extra vars. `machine_login_user` is then `SUDO_USER` when set, else the current user.
6. **Restricted sudo: check, then fail clearly, no fallback.** After `sudo -v`, `machine` runs `sudo -n -l <absolute path of ansible-playbook>`. When its error says that authentication is required, the ticket expired right after `sudo -v` (for example `timestamp_timeout=0`) and the message says so. When sudo refuses, `machine` stops before Ansible with a message naming that command, the need for administrator approval, and `ansible: false`. The failure hint after a failed apply names the same command.
8. **One sudo implementation for the whole run.** A sudo ticket belongs to the implementation that created it, and `sudo` on Ubuntu 25.10+ is sudo-rs while `sudo.ws` is the classic sudo. `machine` uses `sudo.ws` when it exists (as Ansible's `ansible_become_exe` already does), else `sudo`, for `sudo -n true`, `sudo -v`, `sudo -n -l` and the run itself.
9. **InfluxDB values from the environment go into the private extra-vars file.** `group_vars/all/packages.yml` falls back to `INFLUX_*` from the environment when Bitwarden has no value. The run as root gets a fresh environment, so `machine` adds such values to the private extra-vars file it already writes for the Bitwarden values, instead of passing them through `env`, where they would show in the process list.
7. **Remote runs stay as they are.** `--limit <host>` keeps running `ansible-playbook` as the login user with `--ask-become-pass`.

## Implementation outline

- `machine_cli/tools.py`:
  - a helper `local_ansible_prefix(interactive: bool) -> list[str]`: `[]` when `os.geteuid() == 0`; otherwise runs `sudo -v` when `interactive` and `sudo -n true` fails, checks `sudo -n -l <ansible-playbook>` (die with the message of decision 6), and returns `["sudo", "-n", "--", "env", *vars]`;
  - `run_ansible`: for local runs, prefix the command, resolve `ansible-playbook` with `shutil.which`, add `machine_login_user` and `machine_user_session_env` to the JSON extra vars next to `machine_user_path`, and drop the password file. Remote runs unchanged.
  - remove `local_become_password` and its cache.
- `machine_cli/commands.py`: the hint after a failed Ansible apply names `sudo ansible-playbook`.
- `ansible/workstation.yml`: Docker/Compose checks and the play "Touch device" as in decision 3.
- `ansible/roles/touch_device/tasks/main.yml`: `when` on `machine_user_session_env.DBUS_SESSION_BUS_ADDRESS is defined`, `environment` from it; header comment updated.
- `ansible/roles/sshd_home/defaults/main.yml`: `sshd_home_authorized_keys_user` from `machine_login_user` with the old expression as default.
- Docs: `docs/update.md` (one authentication, `sudo -n` without a terminal; the section "Failed apply and restricted sudo" rephrased in general terms for hosts whose sudo refuses `ansible-playbook`, no longer naming managed work machines as the example (owner decision); the command to request), `docs/fingerprint.md` (`machine` asks through sudo once, so the fingerprint works for Ansible).

## Testing

- `tests/unit/test_host_profiles.py` (stubbed `system.run`):
  - local run in a terminal: `sudo -v` once, then `sudo -n -- env ... <abs ansible-playbook>`; no `--become-password-file`, no getpass;
  - ticket already valid (`sudo -n true` succeeds): no `sudo -v`;
  - revert run in the same command: no second `sudo -v`;
  - no terminal and `--no-become`: no `sudo -v`, still `sudo -n`;
  - as root: no `sudo`;
  - `sudo -n -l` refuses: no Ansible run, message names `ansible-playbook` and `ansible: false`;
  - extra vars contain `machine_login_user`, `machine_user_path` and `machine_user_session_env`; `env` gets `MACHINE_HARDWARE` and `ANSIBLE_COLLECTIONS_PATH`;
  - remote run: unchanged command with `--ask-become-pass`, no `sudo`.
- A test that every task or play in `ansible/` with `become: false` is in the allowed list (only the controller-side `stat` in `sshd_home`), so a new login-user task cannot silently run as root.
- `ansible-lint ansible/*.yml`.
- The Docker integration tests in `tests/integration/test_host_yaml_install.py`: the CI laptop host (user `tester` with passwordless sudo, `--no-become`, so `sudo -n`), and `test_install_with_sudo_password` (user `pwtester`, whose sudo asks for a password on Ubuntu 26.04 with sudo-rs and `sudo.ws`). The latter used to hand the password to Ansible through `ANSIBLE_BECOME_PASSWORD_FILE`. It now runs `machine setup` in a pseudo-terminal through `tests/integration/type_password_once.py`, which types the password at sudo's prompt and fails unless exactly one prompt appears (owner decision: the unattended update never runs Ansible, so no password-file path is kept for runs without a terminal).
- By hand on ThinkPad-L13-Yoga-Gen-2 with fingerprint PAM: `machine apply` with the finger, and with the password after the fingerprint timeout; `touch-device` extensions in the GNOME session.

## Risks / Trade-offs

- [The Ansible controller code in the user's home (`~/.local/share/uv/tools/ansible-core`) now runs as root, so a process of the user that can change those files gets root at the next run.] → Today the same user can already change the playbook and the module code that Ansible sends to `sudo`, so the trust boundary does not move. The `sudo -v` ticket expires as usual.
- [A host whose sudo allows only selected commands would refuse the run as root.] → The owner's work hosts allow every command with a password, so none of the known hosts is affected. `machine` checks first and names the command to request; `ansible: false` keeps the rest working.
- [A login-user task added later with `become: false` would run as root.] → The test of the `become: false` list fails for it.
- [`sudo` as root inside the run might still go through PAM on some sudo implementations.] → Task 1.1 checks `sudo.ws` and `sudo-rs` as root; if one authenticates, the plays use `become: false` when `machine` already runs as root.

## Verified facts

Checked on 2026-11-07 on ThinkPad-L13-Yoga-Gen-2 (Ubuntu with `sudo` = sudo-rs and classic sudo as `sudo.ws`, fingerprint PAM; task 1.1):

- `sudo.ws -v` in the terminal shows the fingerprint prompt of `pam_fprintd` and succeeds with a finger.
- With a valid ticket, `sudo.ws -n -l <abs ansible-playbook>` prints the command and exits 0; for a command it cannot run (`/nonexistent/cmd`) it exits 1. Without a ticket it exits 1 with "interactive authentication is required".
- As root, `sudo.ws -n true`, `sudo-rs -n true` and `sudo.ws -n -u <login user> true` succeed without authentication, so the plays' `become: true` and `become_user` need no password during the run as root.
- From root, `sudo.ws -n -u <login user> env DBUS_SESSION_BUS_ADDRESS=... XDG_RUNTIME_DIR=... gnome-extensions list --enabled` lists the user's enabled extensions.
- Under `sudo.ws -n`, `HOME` is `/root` and `PATH` is sudo's secure path; root can run the user's `~/.local/bin/ansible-playbook` (ansible-core 2.21.4) with `ANSIBLE_COLLECTIONS_PATH` set.
- `ansible-galaxy collection list` finds `ansible.posix` for the user in `~/.ansible/collections`.

## Assumptions

- On a host with sudo-rs and without `sudo.ws`, `sudo-rs -n -l <command>` behaves like `sudo.ws` (exit 0 when allowed, non-zero when refused). Only `sudo.ws` was checked by hand and in the integration test; every known host with sudo-rs also has `sudo.ws`.
