# Design

## Context

See [proposal.md](proposal.md) for the operator need. `machine update` already
merges repository changes and applies dotfiles/user-space tools before its
conditional system step. The update state records the last successfully applied
Ansible revision; pending system paths are derived from that revision.

## Goals / Non-Goals

**Goals:** make an explicit one-run skip available from both commands, avoid sudo
and Ansible setup when skipped, and preserve the existing pending-system signal.

**Non-Goals:** changing a host's persistent `ansible` policy, selectively running
parts of a playbook, or suppressing Ansible based on a failed sudo attempt.

## Decisions

- Use the same `--skip-ansible` spelling on setup, apply, and update. It is an
  invocation override; `ansible: false` remains persistent host policy.
- In local apply, sync and validate the host config first, then return before
  bootstrap/system provisioning when explicitly skipped. In remote apply, validate
  the target host config, report the skip, and do not connect or run Ansible.
- In update, preserve fetch/merge, dotfile/tool convergence, and environment
  refresh. Skip only the conditional system apply and do not advance
  `ansible_applied_rev`; existing pending-system detection then exposes remaining
  work to `machine attention` and a later normal apply/update.
- If `--skip-ansible` and `--system` are both supplied, skip takes precedence for
  that invocation and report that system work remains pending.

## Risks / Trade-offs

- A skipped update can contain system files that do not take effect until a later
  apply. The pending-system status and explicit log message make that visible.
- A user may mistake the flag for a persistent setting. CLI help and output state
  that it applies only to the current invocation.

## Migration Plan

No data migration. Existing commands without the flag keep their current behavior.
Verify parser help, local and remote apply behavior, update convergence, and
pending-system detection with isolated unit tests.
