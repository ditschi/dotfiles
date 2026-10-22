# Design

## Context

This change writes the confirmed update behaviour down as baseline specs and changes no code. See proposal.md for the motivation. Current code: `home/dot_local/bin/executable_dotfiles-update-check-job` and the systemd user units, `cmd_update` and `cmd_apply` in `machine_cli/commands.py`, and the helpers in `home/dot_zsh/config/00_alias.zsh`.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep unclear points and goals visible as investigations.

**Non-Goals:**
- Fixes or improvements.

## Decisions

1. **Check in the background, hint in the shell.** A marker file connects them, so shell startup does no network work.
2. **Updates are explicit and safe.** Dirty trees and diverged history stop the update.
3. **Dotfiles and system state are updated together.** Chezmoi runs before Ansible.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Systemd timer.** Today a user timer (10 minutes after boot, then every 6 hours) runs the check job, which fetches, compares `HEAD` with the upstream branch, and writes the marker and a last-check file; setup enables it except on `container`. The owner is unsure about this. Suggestion: confirm the interval, what happens when the host is off or offline, and how the timer behaves on hosts without a user systemd. Why: the hint is only as fresh as the timer.
2. **When Ansible runs.** Today the apply runs when the host profile changed or with `--system`. Suggestion: compare running it on every update, on request only, and when relevant state changed, with their cost and failure modes. Why: updates must cover system and tool state without slow or failing runs.
3. **Restore after a failed apply.** The record says `machine apply` restores the previous `profile.yml` if Ansible or the health check fails on local runs. The owner is unsure. Suggestion: test the failure path and note what is and is not restored. Why: a half-applied profile is hard to debug.
4. **Layout migration offer.** `machine update` still detects the old root-symlink layout and offers migration. The owner says all hosts are migrated. Suggestion: remove the gate once every host is confirmed. Why: it is dead code on migrated hosts.
5. **Reload after a successful update.** Desirable so changes take effect immediately, but not current behaviour. Suggestion: print a reload hint or start a new shell. Why: users otherwise run old config until they restart the shell.
6. **Syncing local changes across machines.** Goal: eventually sync local changes, including edits outside the checkout. Suggestion: first list what can change outside the checkout, then compare approaches by how they detect and keep those edits. Why: the conflict policy depends on what can be lost.
7. **Automatic rollout.** Planned as soon as possible. Suggestion: compare safeguards and rollback options, and decide on which hosts and with which approval. Why: automatic updates must not overwrite local work.
8. **Remote updates.** Possible future improvement, especially for the home server. Suggestion: compare safe, maintainable mechanisms. Why: the home server should not need a manual login to update.
