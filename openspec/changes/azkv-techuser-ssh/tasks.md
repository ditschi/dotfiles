# Tasks

Validation order follows AGENTS.md: the targeted tests of each group, then pre-commit, then the OpenSpec check. Because the change touches the update flow and the work group, a branch review closes the list.

## 1. ssh wrapper and Key Vault helper

- [x] 1.1 Add `home/work/.local/bin/ssh-askpass-azkv`: answers password prompts for `AZKV_ASKPASS_USER` from `AZKV_TECHUSERS` with `az keyvault secret show`, reads other prompts from the terminal, falls back to the terminal with a one-line reason when `az` fails and exits non-zero without a terminal; verify with `pytest tests/unit/test_techuser_ssh.py -q` using fake `az` and a tty file override (`AZKV_ASKPASS_TTY`).
- [x] 1.2 Add `home/work/.local/bin/ssh`: finds the real `ssh` (not itself), uses `ssh -G` to resolve the user, sets or clears the askpass variables, keeps a caller's `SSH_ASKPASS`, runs the real `ssh` unchanged on any other user or when `-G` fails; verify with the same test file (fake `ssh` that prints its environment) for a CI user, another user, an existing `SSH_ASKPASS` and no `AZKV_TECHUSERS`.
- [x] 1.3 Verify that the files are linked only for the `work` group and that bash and zsh login shells resolve `ssh` to the wrapper; verify with the group and login-shell tests in `tests/unit/test_techuser_ssh.py`.
- [x] 1.4 Document the mapping key, the scoping and `ssh-copy-id -i ~/.ssh/id_ed25519_<techuser>.pub <techuser>@<host>` in `docs/ssh.md`, and the key in `docs/secrets.md`; verify the documented commands match the tests and the text names no real vault or host.

## 2. Sync of Bitwarden from Key Vault

- [x] 2.1 Add `machine_cli/techuser_sync.py` (mixin): parse `AZKV_TECHUSERS` from the environment or the env files without executing them, read the secrets with `az`, update the existing Bitwarden login items with `bw_edit_item`, report missing or duplicate items; verify with `pytest tests/unit/test_techuser_sync.py -q` for outdated, equal, missing, duplicate and unreadable cases and that no output line contains a password.
- [x] 2.2 Add `machine secrets sync` to `machine_cli/machine`; verify that `machine secrets sync --help` lists it, and check that `machine secrets <TAB>` completes in bash and zsh (no other new tool is added).
- [x] 2.3 Run the sync as a step of the manual `machine update` before the env pull, only with the mapping set, never in the background update, and without failing the update; verify with update-flow unit tests for order, set, unset and background.
- [x] 2.4 Record an attention item when `az` is not logged in or the vault is unreachable, offer `az login` plus a new sync, clear it after a successful sync; verify with an attention test for both transitions.
- [x] 2.5 Document `machine secrets sync` and the update step in `docs/secrets.md`; verify the text against the spec scenarios.

## 3. Integration

- [x] 3.1 After linking the work group, the owner runs `ssh <agent>` on an agent without the key authorized and confirms that no password is asked, that an agent with the key makes no `az` call, and that `ssh-copy-id` installs the key (design.md Q3); verified by the owner's report of 2026-11-16: `ssh-copy-id` skipped two agents that had the keys and installed them on a third without a password prompt.
- [x] 3.2 Run `pytest tests/unit/test_techuser_ssh.py tests/unit/test_techuser_sync.py tests/unit/test_bitwarden_session.py tests/unit/test_ssh_client.py -q`, then `pre-commit run --files <changed paths>`, then `openspec validate azkv-techuser-ssh --strict`; verify all pass.
- [x] 3.3 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent) and fix the findings before archive; verify that no open findings remain.

## Workflow follow-up

- Archive the change after validation and review (archive flow in `openspec/config.yaml`).
