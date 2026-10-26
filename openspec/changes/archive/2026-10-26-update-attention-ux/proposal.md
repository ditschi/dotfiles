# Proposal

## Why

An update that only overlaps with local edits by file name ends in the needs-attention state, although git could merge both sides without a conflict. The owner then sees `machine` offer `machine update` again, which stops for the same reason. `machine status` contradicts itself: it says `update pending: no` while the checkout is 7 commits behind. The status is also long and hard to read. The owner expects an update to keep local changes and continue whenever they merge cleanly, also in the background job. When there is a real conflict, the owner expects to be told clearly what conflicts and to resolve it by hand, unless the owner actively chooses to put the conflicting changes aside. A diverged history whose local commits rebase cleanly should not stop a manual update either.

## What Changes

- The blocking check for overlapping files becomes a trial merge. Local changes that merge cleanly with the incoming commits are kept and the update continues. This holds for `machine update` and for the background update. **BREAKING** for the recorded decision "the state is needs-attention and the user merges" (archived `update-classification` design), which now applies only to real conflicts.
- On a real conflict, an interactive `machine update` or `machine attention` shows a colored diff of the conflicting files and offers two choices: resolve manually outside `machine` (default; the commands are shown) or put only the conflicting changes into a named stash entry and update. Without a terminal it stops.
- `machine update --force` makes the stash choice without asking; cleanly merging changes stay in place.
- Every stash entry that `machine` creates is restored completely or kept with an attention item until the user restores or drops it. This includes the background job's revert, which today runs `git reset --hard` and would lose local changes.
- When the history diverged, a manual `machine update` rebases the local commits onto the upstream if a trial rebase is clean and the commits are safe to rewrite (not on a remote branch, no merge commits, no signing, no operation in progress). The background job does not rebase.
- A manual update runs the zsh health check like the background job; the attention item for a reverted automatic update shows the failed check's output.
- The attention list shows the update item first and does not offer `machine apply` on the old checkout while the update is blocked.
- lazygit is installed with mise on every host; `machine` does not start it.
- After the user resolves the conflict, `machine` or `machine attention` runs the full update, including the system step (Ansible) when it is pending.
- The attention item for a blocked update no longer offers a plain re-run that is certain to fail.
- The needs-attention reason names the files, the number of incoming commits and which files actually conflict. The error is the last line of output.
- `machine status` takes "behind" and "pending" from the live check, so it no longer contradicts itself. It becomes a compact, colored overview (colors only on a terminal; `NO_COLOR` is honored). `machine status -v` shows the full host config, dotfile groups and file lists.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `update-flow`: "Update never discards local work" (trial merge instead of a file-name overlap; clean merges continue; conflicts stop with a diff), "Attention entry point" (the update item shows the conflict and continues the full update after it is resolved), "Read-only update check" (the check reports conflicting files separately from cleanly merging ones; `machine status` is compact, colored and has `-v`), "Explicit update" (blocked automatic update only on a real conflict), "Automatic update safety net" (revert keeps local changes); new requirements for conflict choices, `--force`, stash entries, clean rebase, the zsh check after a manual update, the attention reason and the status.
- `user-tools`: lazygit in the `core` tools.

Affected hosts: all hosts that run `machine` (private and work, desktop, server and container); the background job runs where the update timer is enabled.

## Impact

- Code: `machine_cli/updates.py` (plan, merge, state, printing), `machine_cli/auto_update.py` (background job uses the same merge rule), `machine_cli/attention.py` (update item), `machine_cli/commands.py` (`cmd_status`), `machine_cli/machine` (`status -v`).
- `home/core/.config/mise/conf.d/10-shell.toml` and `mise.lock` (lazygit).
- Uses the existing git pager setup (`delta` from mise when installed, else `less`) for the colored diff; no new dependency.
- Tests: `tests/unit/test_update_and_env.py`, `tests/unit/test_machine_cli.py`.
- Docs: Readme section on `machine update`, `machine status` and `machine attention`.
