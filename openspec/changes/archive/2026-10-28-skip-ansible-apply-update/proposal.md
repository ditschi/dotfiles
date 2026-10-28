# Proposal

## Why

The owner needs to run `machine apply` or `machine update` when Ansible cannot
currently obtain the required sudo authorization. The host-config `ansible: false`
setting is persistent policy, so a separate per-invocation option is needed for
temporary skips.

## What Changes

- Add `--skip-ansible` to `machine apply` and `machine update`.
- Keep host configuration, repository update, dotfile, and user-space tool behavior
  unchanged when the option is used.
- Leave unapplied system changes detectable and report that Ansible was skipped.
- Do not write `ansible: false` or otherwise change persistent host policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-profiles`: one-invocation Ansible skip behavior for apply and update.

## Impact

`machine_cli/machine`, `machine_cli/commands.py`, `machine_cli/updates.py`,
unit tests, and the `machine-profiles` specification. A skipped invocation does
not perform system provisioning or mark Ansible as having applied the current
revision.
