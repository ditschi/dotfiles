# Design

## Context

See proposal.md for the motivation.

Today `run_ansible` in `machine_cli/tools.py` calls `local_ansible_prefix`, which authenticates (`sudo -n true`, then `sudo -v` in a terminal) and checks `sudo -n -l ansible-playbook`. `machine update` reaches that point last: `_update_steps` in `machine_cli/updates.py` runs env pull, dotfile apply, tool install, syncthing ignores, zsh check and only then decides whether to run Ansible (`saved_ansible()` and host config changed, `--system`, or system files relevant) and calls `cmd_apply`. `cmd_apply` in `machine_cli/commands.py` runs `ensure_bootstrap_tools` (which can install uv, ansible-core and Bitwarden) before `run_ansible_or_hint`. The decision inputs for `update` (`profile_changed`, `args.system`, the plan `steps`, `saved_ansible()`, `--skip-ansible`) are all known at the start of `_update_steps`.

A sudo ticket lasts 15 minutes by default (`timestamp_timeout`).

## Goals / Non-Goals

**Goals:**
- One sudo prompt at the start of `update` and `apply` when Ansible will run, no prompt when it will not.
- A restricted-sudo host fails at the start, not after the tool install.

**Non-Goals:**
- `machine setup`, remote runs and the automatic update (owner decisions below, or unchanged).
- A background process that keeps the ticket alive, and changes to the sudo configuration.
- Changing how Ansible runs as root (`ansible-single-sudo`).

## Decisions

1. **Authenticate and check at the decision point (owner decision, 2026-11-09).** The sudo steps of `local_ansible_prefix` (installed check, `sudo -n true` / `sudo -v`, `sudo -n -l <ansible-playbook>`) become one callable that raises `CalledProcessError` as today. `_update_steps` calls it right after `profile_changed` is known and before `env pull`, only when the existing condition for running Ansible holds; the condition is computed once and reused by the Ansible step at the end. `cmd_apply` calls it before `ensure_bootstrap_tools`, inside the existing `try`, so a failure restores the host config like a failed Ansible run.
2. **Renewed check before Ansible (owner decision, 2026-11-09).** `local_ansible_prefix` keeps calling the same callable, so a still-valid ticket costs two quick `sudo -n` calls and an expired one prompts again right there. In `apply`, the callable is also called again after the bootstrap tool install, so that a failure there stays a sudo failure without a recovery run. Rejected: only the early authentication, because a long tool install can outlast the ticket and the run would then fail.
3. **Both `update` and `apply` (owner decision, 2026-11-09).** `apply` has fewer slow steps before Ansible but `ensure_bootstrap_tools` can install tools, and one rule for both is simpler.
4. **The automatic update is unchanged (owner decision, 2026-11-09).** It never runs Ansible, so it has nothing to authenticate.
5. **Failure at the early check: do everything that needs no root (owner decision, 2026-11-09).** A typo does not count as a failure: sudo itself asks again up to its `passwd_tries` (3 by default) within one `sudo -v`, and `machine` adds no prompt round. The check fails only when sudo gives up, because the password was wrong in every try or because the user has no sudo permission (this includes sudo refusing `ansible-playbook` as root). In `update`, the failure is logged at once, recorded as the failed step `ansible apply`, every step that needs no root runs with the new host config, Ansible is skipped, and a changed host config is restored at the end so that it only counts as applied when Ansible ran with it; the next update applies it again. A cancelled prompt (Ctrl+C) is an ordinary failure of the check and takes the same path. In `apply`, it follows the existing failure path: the user steps before the check have run, Ansible does not, and the host config is restored; the recovery Ansible run for a changed host config is skipped, because it would need the same sudo. Rejected: aborting the whole update, because dotfile and tool updates would be lost.
6. **The failure reason names its cause.** The authentication runs `sudo -v` with the locale forced to `C` and reads sudo's stderr (sudo prompts on the terminal, so the prompt stays visible): `incorrect password attempt` gives "wrong password", `may not run sudo` or `not in the sudoers file` gives "no sudo permission", anything else keeps the generic text. The text only chooses the message; every non-zero exit is a failure either way. Rejected: guessing from group membership, because sudoers can grant rights through other groups or user entries.
7. **`--no-become` and no terminal** keep today's behaviour of the callable: no prompt, `sudo -n` only, the existing message, now at the start.

## Risks / Trade-offs

- [The steps in `update` outlast the ticket] → Decision 2: prompt again right before Ansible. A keep-alive is not added.
- [`env pull` asks questions after the sudo prompt, so the first prompt is not the only one] → Only sudo prompts are removed from the middle of the run; the questions are unchanged.
- [The new code path runs in `update` before `hand_over_to_new_code` finished] → The call sits in `_update_steps`, which runs with the new code after the hand-over, so no extra case.
- [Two sudo checks per run] → `sudo -n true` and `sudo -n -l` are quick and non-interactive when the ticket is valid.

## Migration Plan

Nothing to migrate. Rollback is a normal update to the previous commit.

## Open Questions

None. The stderr texts were checked on 2026-11-09 against classic sudo (`sudo.ws`) and sudo-rs 0.2.13 in a throwaway Ubuntu 24.04 container with a pseudo-terminal for the prompt:

- Wrong password in every try: classic `sudo: 3 incorrect password attempts`; sudo-rs `sudo: maximum 3 incorrect authentication attempts` (after `sudo: Authentication failed, try again.` twice). Classic prints `Sorry, try again.` on the terminal, sudo-rs on stderr.
- User without sudo permission, with a right or a wrong password (no prompt for the password is read): classic `Sorry, user <user> may not run sudo on <host>.`; sudo-rs `sudo: I'm sorry <user>. I'm afraid I can't do that`. The classic text `<user> is not in the sudoers file` is kept as a pattern but was not seen.
- Without a terminal both refuse with `a terminal is required` / `A terminal is required to authenticate`, which is the existing no-terminal path.
