# Design

## Context

See proposal.md for the motivation. Current behaviour:

- `update_plan` (`machine_cli/updates.py`) treats any path that is changed locally and changed by the incoming commits as an overlap and a blocker. It does not check whether git can merge both sides.
- A manual `machine update` writes the needs-attention state on an overlap, prints `git status --short` and then stops with `manual attention needed: … (--force stashes them, merges and restores them)`. It does not set `pending`.
- The background job (`machine_cli/auto_update.py`) stops on any remaining local change, also on changes that the incoming commits do not touch. If an automatic update breaks zsh or an apply step, it reverts with `git reset --hard <previous>`.
- The attention item for a blocked update (`machine_cli/attention.py`) asks "Run `machine update` now?" and runs it without `--force`, so it stops again.
- `machine status` (`machine_cli/commands.py`) prints raw `git status -sb`, `update pending` from the state file, the state, the plan, and the full host config and dotfile-groups file.
- The shared gitconfig sends `git diff` through `delta` (from mise) when it is installed, else `less -FXRi`. meld is configured as the difftool and mergetool.

Observed on the owner's laptop: the checkout was 7 commits behind, `Readme.md` and `ansible/group_vars/all/features.yml` were changed on both sides, and a trial merge with `git merge-tree` was clean.

## Goals / Non-Goals

**Goals:**
- An update keeps local changes and continues whenever they merge cleanly, in manual and background runs.
- A real conflict stops everything and shows the user what conflicts and how to resolve it.
- Status and attention output give the reason and the next command without contradiction.

**Non-Goals:**
- Starting a merge tool (meld, lazygit) from `machine`; conflicts are resolved outside it.
- Changes to the shell prompt segment or the shell-start message beyond the reason text they already show.
- Auto-resolving conflicting hunks.

## Decisions

### Trial merge decides whether files conflict
`update_plan` builds a commit of the tracked local changes with `git stash create` (no stash entry, nothing changes) and runs `git merge-tree --write-tree --merge-base=HEAD <upstream> <stash-commit>`. Exit code 0 means clean; on 1 it reads the conflicting paths from the `--name-only` output. Untracked files are not in the stash commit, so an untracked path that the incoming commits add counts as a conflict. The plan gains `merged` (overlapping and clean) and `conflicts`; only `conflicts` are blockers. `overlap` stays in the JSON for compatibility with the background job during the change.

Requires git 2.38 or newer for `merge-tree --write-tree` and 2.40 for `--merge-base`. When git is older, every overlap counts as a conflict, as today.

Alternative rejected by the owner: keep stopping on every overlap and let the user merge. It produced a needs-attention state for changes git merges without help.

### Clean merges are applied with `git merge --ff-only --autostash`
Git stashes the local changes, fast-forwards and re-applies them. Because the trial merge was clean, re-applying succeeds. If it does not, git keeps the changes as a stash entry; the update stops with needs-attention and the reason names the stash, so no work is lost. The same call is used in the background job.

### Conflict choices
On a conflict, nothing is changed until the user chooses. An interactive run first shows `git diff HEAD -- <conflicting files>` through the configured git pager (delta when installed) and `git log --oneline HEAD..<upstream> -- <conflicting files>`, then offers:

1. Resolve manually (default). Prints the commands below and the reason; nothing changes. The user resolves outside `machine` with any tool (meld is configured as `git mergetool`).
2. Put the conflicting changes into the stash and update. Only the conflicting paths go into `git stash push -m "machine update <date>: conflicting with <upstream short sha>" -- <paths>`; the other local changes are kept through `--autostash`. An attention item names the entry and offers to restore it later.

A run without a terminal prints only the reason and stops.

Manual commands printed by option 1:

```
git stash && git merge --ff-only <upstream> && git stash pop
git mergetool            # or edit the conflict markers by hand
git stash drop           # once the files are resolved
machine
```

The stash choice is never the default and never runs without the user choosing it, because it removes local work from the working tree. Its attention item stays until the entry is restored or dropped, so the work is not forgotten.

### `--force` is the stash choice without asking
`machine update --force` runs option 2: update to the upstream, keep everything that merges cleanly, stash only the conflicting changes with an attention item. It never discards changes and never forces through a conflict in the files.

### Restoring stashed changes is guaranteed
Every stash entry `machine` creates has a message `machine update <ISO date>: <why>` and is recorded in the update state (`stash=<sha>`). Re-apply uses `git stash apply <sha>` and drops the entry only after the apply succeeded with no conflict left. If the apply conflicts, the files keep the markers, the entry is kept and the commands to finish by hand are printed. The attention list and `machine status` show every recorded entry that still exists and every entry whose name starts with `machine update ` (so entries from an older state file are found too); the user's own stash entries are left alone. The attention item shows `git stash show --stat` and asks restore / drop / keep, keeping by default. Unit tests cover the failure paths (apply conflicts, apply fails, entry dropped by hand).

### Manual update runs the zsh health check
The background job already checks zsh after an update. A manual update now runs the same check after the dotfile apply. It does not revert, because the user is present; it shows the check output, does not replace the shell and sets needs-attention. The attention item for a reverted automatic update shows the stored check output before offering `machine update`.

### Attention item order
The update item comes first. While the update is blocked, the system item is shown as part of it ("the system step runs after the update") instead of offering `machine apply` on the old checkout.

### lazygit in `core`
lazygit is added to `home/core/.config/mise/conf.d/10-shell.toml` (registry backend `aqua:jesseduffield/lazygit`), so it is installed on every host like delta. `machine` does not start it or any other resolution tool.

### Background job continues with local changes
The background job no longer stops on local changes that the incoming commits do not touch or that merge cleanly; on a conflict it only records needs-attention (it never stashes). Before the fast-forward it stores the local changes as a named stash entry (`git stash store -m "machine update-auto <date>: before update" $(git stash create)`), recorded as in "Restoring stashed changes is guaranteed". A revert runs `git reset --hard <previous>` and then `git stash apply` of that entry; the entry is dropped only after the apply succeeded, otherwise it stays with an attention item. After a successful update without revert the entry is dropped. Untracked files are not touched by the reset.

### Diverged history: clean rebase in a manual update
A diverged history usually means a local commit that was not pushed yet, and the shared gitconfig already rebases on pull. A manual `machine update` therefore rebases without asking when it is safe. The trial uses `git replay --onto <upstream> <upstream>..HEAD` (in memory; nothing changes). The rebase itself runs `git rebase --autostash <upstream>` only when all guards hold:

- no local commit is on any remote branch (`git branch -r --contains`), because rebasing creates copies with new IDs and pushed copies would then appear twice;
- no merge commit among the local commits, because a plain rebase flattens them;
- commit signing is off, because re-signing needs the key and can fail halfway;
- no rebase, merge or cherry-pick is in progress.

If the real rebase fails anyway, it is aborted, so the checkout is as before. The background job does not rebase; rewriting commits while the user may be working in the repository is left to a manual run. The reason for a stop names the number of local and incoming commits and `git pull --rebase`.

Alternatives considered: rebasing in the background job too (rejected by the owner: background rewrite of local commits); never rebasing automatically (rejected: the stop is unnecessary when the rebase is clean).

### Attention item follows the live plan
The update item re-runs the plan without fetching. With conflicts it shows the diff and the conflict choices (manual by default). Without conflicts it offers "Run the update now?" (default yes), which runs the full update including Ansible when the system step is pending.

### Reason text and output order
The reason is built from the plan: `<n> commits incoming; conflict in <files> → resolve, then run: machine`. For a diverged history: `<n> local and <m> incoming commits; history diverged → run: git pull --rebase, then machine`. `merge_upstream` no longer prints `git status --short` before stopping; the reason is the last line.

### Status layout
`machine status` uses `rich` (already a dependency; it disables colors when stdout is not a terminal and honors `NO_COLOR`). Rows: repo (branch, behind/ahead count, last check), attention (only when set; reason and next command in yellow or red), incoming (count and steps), local (counts of modified, untracked, merged, conflicting), host (host name, context, device, config in sync), features (`rich.columns.Columns`), groups (one line). `-v` adds the incoming and local file lists, the host config and the dotfile groups file. The `update pending` line is removed; "behind" comes from the live plan.

## Risks / Trade-offs

- [Rebase rewrites local commit IDs] → only commits that are on no remote branch.
- [Trial merge says clean but `--autostash` re-apply fails] → git keeps a stash entry; the update stops and the reason names it.
- [Background job now changes a dirty checkout] → only for clean merges, the local changes are re-applied, and a revert re-applies them too.
- [Untracked directories under a path the upstream adds] → counted as conflicts; better a false stop than an overwritten file.
- [Older git without `merge-tree --write-tree`] → falls back to the file-name rule.
