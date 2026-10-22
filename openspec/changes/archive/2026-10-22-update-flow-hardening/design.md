## Context

See proposal.md for motivation. `health_check_after_apply` in `tools.py` sets `ok = True` and only logs a warning for telegraf. Its comment records that earlier checks (`sshd -t` as a normal user, `sudo -n`) rolled back successful applies, because they need root. `cmd_apply` restores `profile.yml` when the check returns false.

`_update_locked` takes the profile backup before `sync_host_profile_from_repo()` and passes `profile_backup` and `profile_changed` to `cmd_apply`. The automatic path (`auto_update.py`) already reverts and records the failed revision; only the spec is missing.

## Goals / Non-Goals

**Goals**
- A health check that can fail without false positives.
- The update timer fires on headless hosts too.
- Tests for the failure paths that are only exercised through stubs today.

**Non-Goals**
- `machine update --rollback`, staged rollout or a `stable` channel (owner decision: not now; the `update-flow` spec also forbids a `rollback` subcommand for the old layout migration).
- Running Ansible automatically.
- A reload hint after `machine update`: the prompt segment already covers it.

## Decisions

- The health check can fail (owner decision). Checks must run as a normal user without sudo. The owner chose two failing checks: the existing zsh startup health check, and the chezmoi config being readable with `chezmoi verify` not erroring (when chezmoi is installed and the config exists). Both need no privileges.
- The telegraf check stays a warning. The comment in the code says it can be inactive right after the first apt install, which would be a false failure.
- The job script is tested against a local bare repository with the fetch and marker behaviour only; the `machine update --auto` path is covered by existing unit tests.
- Linger is enabled on every host that has `loginctl` and is not a container, not only on headless profiles (owner decision: the owner is confident it is not active yet, and one rule avoids a per-profile list). It is best effort: a failure (for example missing admin rights on a work machine) is logged with the manual command and never stops setup or update. It lives next to the timer enablement in `ensure_update_timer`, which `machine setup` now reuses, so both commands behave the same.
- The safety net requirement is specified as behaviour (revert, no retry, needs-attention) without naming the files that hold the state.

## Risks / Trade-offs

- A new failing check could roll back a good apply, as happened before → every check must work unprivileged; add a unit test per check with the failing and the passing case.
- `enable-linger` changes the host (the user manager and enabled user services start at boot and stay after logout) → best effort, skipped without `loginctl` and in containers, failure is only logged.

## Open Questions
