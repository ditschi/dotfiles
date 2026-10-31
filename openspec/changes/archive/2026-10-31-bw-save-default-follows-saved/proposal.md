# Proposal

## Why

When a saved Bitwarden session token has to be renewed, the question whether to save the token offers "no" as default, although the owner already chose to save it before. The owner wants the default to follow that earlier choice: yes when a token is already saved.

## What Changes

- The question whether to save `BW_SESSION` in `~/.env.local` defaults to yes when `~/.env.local` already holds a `BW_SESSION`, and stays no otherwise. This affects the question in `machine setup` and the offer after a fresh unlock.
- In `machine setup`, an explicit "no" while a token is saved removes `BW_SESSION` from `~/.env.local` and keeps the CA/proxy settings, because the renewal has already written the new token there by then (owner decision).
- Unchanged: `machine update` and `machine env pull` replace a saved token on renewal without asking, and nothing is saved without a terminal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `secret-tools`: the requirement "Session storage is opt-in" gets a default that follows an earlier save, and a "no" removes a saved token.

Profiles: every host that uses Bitwarden (private and work; not containers, which skip Bitwarden).

## Impact

- Code: `machine_cli/bw_client.py` (`setup_bitwarden`, `offer_saving_bitwarden_session`, a helper that removes the saved token).
- Tests: `tests/unit/test_bw_and_answers.py`.
- Where the change is made: the existing git worktree `.claude/worktrees/lucid-euclid-47f907`, not the main clone, because `machine_cli/` is read live by the host's `machine`; the session already runs in this worktree, so no further worktree is nested.
