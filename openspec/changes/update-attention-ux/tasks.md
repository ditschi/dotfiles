# Tasks

## 1. Trial merge in the update plan

- [x] 1.1 In `update_plan` (`machine_cli/updates.py`) split overlapping paths into `merged` and `conflicts` with `git stash create` + `git merge-tree --write-tree --name-only --merge-base=HEAD`; count untracked paths that the incoming commits add as conflicts; fall back to "all overlaps conflict" on older git. Only conflicts become blockers. Verify with unit tests in `tests/unit/test_update_and_env.py` on a temporary repo: clean overlap → `merged`, conflicting hunk → `conflicts`, untracked vs added path → `conflicts`.
- [x] 1.2 Show `merged` and `conflicts` in `print_update_plan` and in `--json`; verify with a test of `machine update --check` output.

## 2. Stash entries that are never lost

- [x] 2.1 Add helpers that create a named stash entry (`machine update <ISO date>: <why>`), record it in the update state, re-apply it with `git stash apply`, and drop it only after a complete apply with no conflict left; on a failed apply keep the entry and set needs-attention naming it. Verify with tests: clean apply drops the entry; conflicting apply keeps entry and markers; entry dropped by hand clears the record.

## 3. Manual update: clean merges, conflict choices, `--force`

- [x] 3.1 Replace the stash/pop in `merge_upstream` with `git merge --ff-only --autostash`; if git leaves a stash entry, stop with needs-attention naming it. Verify with a test: overlapping clean change → checkout at upstream, both changes present, no stash entry.
- [x] 3.2 On conflicts: no `git status` dump; on a terminal show `git diff HEAD -- <files>` through the git pager and `git log --oneline HEAD..<upstream> -- <files>`, then offer "resolve manually" (default, prints the commands) or "stash the conflicting changes and update" (uses 2.1, keeps clean merges). Without a terminal stop. Always set `pending` and the needs-attention reason (commit count, conflicting files, next command) and print the reason last. Verify with tests for default choice, stash choice and non-interactive run.
- [x] 3.3 Make `--force` run the stash choice without asking; update its help text. Verify with a test: one clean and one conflicting file → checkout at upstream, clean file keeps its change, conflicting change in a named entry, attention item listed.
- [x] 3.4 Run the zsh health check after a manual update that applied home files; on failure show the output, do not replace the shell, set needs-attention. Verify with a test that stubs a failing check.

## 4. Diverged history

- [x] 4.1 In a manual update, when the history diverged: trial with `git replay --onto <upstream> <upstream>..HEAD`; check the guards (no local commit on a remote branch, no merge commit, `commit.gpgsign` off, no operation in progress); if all hold run `git rebase --autostash <upstream>` (abort on failure) and continue. Otherwise stop with the reason `<n> local and <m> incoming commits; history diverged → run: git pull --rebase, then machine`. Verify with tests for each guard and for a clean rebase.
- [x] 4.2 Keep the background job from rebasing; it records the new reason. Verify with a test.

## 5. Background job

- [x] 5.1 In `_update_auto_locked` stop only on conflicts or divergence; continue with unrelated or cleanly merging local changes using the same merge as 3.1. Verify with tests: unrelated local change → updated and kept; conflicting change → needs-attention with the new reason, no stash entry.
- [x] 5.2 Store the local changes as a named stash entry (2.1) before the fast-forward; drop it after a successful update; after `reset --hard` in `_revert_auto` re-apply it. Store the failed check output for the attention item. Verify with a test where the zsh health check fails: local changes present after the revert, entry gone; and one where the re-apply fails: entry kept, attention item listed.

## 6. Attention items

- [x] 6.1 Rebuild the update item in `machine_cli/attention.py` from the live plan: conflicts → diff and conflict choices; no conflicts → offer the full update (including Ansible when the system step is pending); reverted update → show the stored check output first. Verify with tests for each case.
- [x] 6.2 List the update item first; while it is blocked, show the pending system step inside it and do not offer `machine apply`. Verify with a test with both items open.
- [x] 6.3 Add the stash-entry item: offer to restore (2.1); on a conflict keep the entry and print the commands. Verify with a test.
- [x] 6.4 Recognise `machine` stash entries also by name; the item shows the content and offers restore / drop / keep (default keep). Verify with tests for keep, drop and an unrecorded entry found by name.

## 7. Status

- [x] 7.1 Rewrite `cmd_status` (`machine_cli/commands.py`) as the compact `rich` overview from design.md, drop `update pending`, take behind/pending from the live plan; add `-v` in `machine_cli/machine`. Verify with tests: default output has no host-config YAML, `-v` has it, no ANSI codes when not a terminal or with `NO_COLOR`, blocked update shows "behind" and the conflict.

- [x] 7.2 Show the number of stash entries put aside by `machine` with the hint to decide in `machine attention`; list them with `-v`. Verify with a test that counts only entries named by `machine`.

## 8. lazygit and docs

- [x] 8.1 Add `lazygit = "latest"` to `home/core/.config/mise/conf.d/10-shell.toml`, update `mise.lock`, and add lazygit to the core tool list in the Readme. Verify `mise install` puts `lazygit` on the PATH and `pytest tests/unit -q` passes.
- [x] 8.2 Update the Readme sections on `machine update` (clean merges, conflict choices, `--force`, rebase), `machine status` and `machine attention`; verify the documented commands and output match.

- [x] 8.3 Let `machine_cli/mise_check.py` read the fragments from `git ls-files` (tracked and not ignored), so ignored nested checkouts such as `.claude/worktrees/` do not count. Verify `python3 -m machine_cli.mise_check` passes with the stale worktree present and `tests/unit/test_mise_check.py` passes.

## 9. Validation

- [ ] 9.1 Run `pre-commit run --all-files` and `pytest tests/unit -q`; both pass.
- [ ] 9.2 On the owner's laptop reproduce the original case (local edit in a file changed upstream, clean merge): `machine update` updates without a prompt and keeps the edit; a conflicting edit stops with the diff and the manual default; an unpushed local commit is rebased.

## Workflow follow-up

- Archive the change; make sure the archived design.md states that clean overlaps are merged automatically (replacing the overlap decision of `update-classification`), the conflict choices, `--force`, and the rebase guards.
