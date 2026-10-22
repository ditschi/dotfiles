# Proposal

## Why

The owner wants the health check after `machine apply` to be able to fail. Today `health_check_after_apply` always returns true, so the documented revert of the host profile on a failed health check cannot happen in production. The automatic update has a safety net (revert, no retry, needs-attention) that is described only in an archived design and in the Readme, not in the `update-flow` spec. The update-check job script and the update flow through `machine update` have no tests.

## What Changes

- The health check after a local apply can return failure, using only checks that work without root and without cached sudo credentials, so a successful apply is not rolled back by mistake.
- Add a requirement to `update-flow` for the unattended safety net: after an automatic update, a failing zsh health check or a failing `chezmoi apply` resets the checkout to the previous revision, the failed revision is not retried until a manual update succeeds, and the state becomes needs-attention with the reason.
- Add tests: `machine update` with a changed host profile and a failing Ansible run (the profile is reverted), the health check failure path, and the update-check job script against a local bare repository.
- `machine setup` and `machine update` enable systemd linger for the user (best effort), so the update timer also runs on headless hosts without a login session.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `update-flow`: the timer requirement also enables linger; new requirement for the revert, no-retry and needs-attention behaviour of the automatic update; the apply-failure behaviour (health check can fail, profile restored) is stated as a requirement.

## Impact

- Affected profiles: all that run `machine apply` locally (health check) and all that have the update timer (job test). Linger matters most for hosts without a login session (home server, rpi, rpi-zero) and is enabled on every host with `loginctl`, except containers.
- Code: `home/dot_local/lib/machine_cli/tools.py`, `commands.py`, `updates.py`, `auto_update.py`, `home/dot_local/bin/executable_dotfiles-update-check-job`.
- Tests: `tests/unit/test_host_profiles.py` and a new job-script test.
- Docs: Readme (apply and update sections).

## Assumptions

- Already covered, so not part of this change: `GIT_TERMINAL_PROMPT=0` is set in `dotfiles-update-check.service`; the prompt segment tells the user to reload the shell after an update (spec "Shell older than the applied update").
- The profile backup in `_update_locked` is taken before the sync and passed to `cmd_apply`. This was read from the code, not executed; the new test confirms it.
