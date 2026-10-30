# Proposal

## Why

When `~/.env` or `~/.env.host` contain keys that neither Bitwarden nor `~/.env.local` set, the sync prints one long line that names neither the cause nor the next step, and it aborts the rest of `machine update`. The user should be able to resolve each key on the spot, and an update should not fail because of it.

## What Changes

- `machine env pull`, `machine update` and `machine setup` no longer abort when an existing env file holds keys without a source ("local-only keys"). The generated file is written anyway, and the local-only keys are carried over into a marked section at its end, so they stay set in the shell and new Bitwarden values still arrive.
- On a terminal (and without `--yes`), the sync asks per local-only key: add it to the Bitwarden item that belongs to the file, keep it in `~/.env.local`, remove it, or skip (decide later). The item name is shown in the prompt. "Skip" is preselected. A key that a Bitwarden item set before but no longer sets is shown with that item, as a hint that it was deleted in the vault.
- "Add to Bitwarden" appends the original line to the item's notes under an origin comment, syncs and regenerates the file. A failed write behaves like skip.
- Skipped keys and keys met without a terminal stay in the local-only section and appear as an item in `machine attention`, which offers the same choices.
- **BREAKING** (behaviour): `machine` no longer moves local-only keys into a new `~/.env.local` by itself. `~/.env.local` is changed only when the user picks "keep locally", and then only by appending.
- An env file with lines that are not plain assignments (shell code) is left unchanged; it gets an attention item that offers keep locally, remove or skip.
- The message for unresolved keys is short and actionable: which keys, which file, which Bitwarden item, the backup path and the command that resolves them.
- Local-only keys never make an update fail and never trigger a revert.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `env-files`: `~/.env.local` is appended to with the user's consent instead of being untouched; local-only keys are carried over in a marked section; new requirements for resolving local-only keys (choices, skip as default, Bitwarden write, non-interactive behaviour, no abort or revert).
- `update-flow`: the attention entry point lists env files with local-only keys or shell code and offers their choices.

Affected contexts: `private` and `work` (both have a group item); containers have no context and skip the env sync, as today.

## Impact

- Code: `machine_cli/env_pull.py` (sync, carry-over section, choices, Bitwarden notes write), `machine_cli/attention.py` (new env item), `machine_cli/updates.py` and `machine_cli/commands.py` (callers no longer stop on the env sync), `machine_cli/machine` (`env pull` passes the interactive flag as today). Bitwarden writes reuse `bw_get_item_raw` / `bw_edit_item` from `machine_cli/bw_client.py`.
- Tests: `tests/unit/test_update_and_env.py` (env pull cases that currently expect `SystemExit`), attention tests.
- Docs: Readme section on env files.
- Bitwarden: the group or host env item may gain lines in its notes, written only after the user picks that choice.
- Where: git worktree `.worktrees/env-pull-resolve-local-keys` on branch `env-pull-resolve-local-keys`, because the change touches `machine_cli/`, which the live host runs from the main clone.
