## Why

Since the managed SSH config gets mode `0600` during dotfile apply, setup fails when the checkout is mounted read-only: `chmod` raises `Read-only file system` and the apply step reports a failure. This breaks every Docker profile test (the tests mount the repository read-only at `/dotfiles`) and the extended setup of `sdx`, which runs `bootstrap` from a read-only mount at `/mnt/dotfiles` under `set -e`.

## What Changes

- Dotfile apply leaves the managed SSH config alone when it already has mode `0600`.
- When the checkout is on a read-only file system, dotfile apply and the SSH client apply report that the mode could not be set and continue instead of failing.
- Other `chmod` errors still fail the apply, as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-layout`: "Managed SSH config has owner-only permissions" gains the read-only checkout case.
- `ssh-client-config`: "Config file mode" gains the read-only checkout case.

## Impact

- Code: `machine_cli/dotfiles.py` (`run_dotfiles_apply`), `machine_cli/ssh_client.py` (`apply_ssh_client`).
- Tests: `tests/unit/test_dotfiles.py`, `tests/unit/test_ssh_client.py`; the Docker profile tests in `tests/integration/` pass again.
- Profiles: all contexts and devices that select the group providing `.ssh/config`; in practice containers and `sdx` sessions with a read-only checkout.
- Where the change is made: worktree `~/dotfiles/.worktrees/ssh-config-permissions-readonly-checkout` on branch `ssh-config-permissions-readonly-checkout`, because it changes `machine_cli/`, which the live checkout serves to the host.

## Assumptions

- The owner was not available when this was planned. Tolerating only a read-only file system (not other permission errors) is the narrowest change that unblocks the read-only mounts while keeping the recorded expectation that permission errors fail the apply; the owner should confirm or choose another approach (for example copying the checkout into the test containers instead).
