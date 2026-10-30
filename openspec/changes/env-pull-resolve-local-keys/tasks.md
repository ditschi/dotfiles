# Tasks

All work happens in the worktree `.worktrees/env-pull-resolve-local-keys`.

## 1. Classify existing env content

- [x] 1.1 In `machine_cli/env_pull.py`, add a parser for an existing env file that returns: generated or hand-written (header), each assignment line with its key and origin (Bitwarden section `# --- <item> ---`, local-only section, or hand-written) and the shell-code lines (non-comment, non-assignment, or not parseable by `shlex`); verify with new unit tests in `tests/unit/test_update_and_env.py` for a hand-written file, a generated file with a local-only section, and a file with an `if … fi` block
- [x] 1.2 Compute the local-only keys per file (existing keys minus generated keys minus `~/.env.local` keys) and the Bitwarden item a vanished Bitwarden-section key came from (`# was in <item>` when carried over); verify with unit tests

## 2. Sync never aborts; carry-over section

- [x] 2.1 Replace the automatic move into a new `~/.env.local` and the `die()` with: write the generated file plus the local-only section (original lines, unchanged) when the file has no shell code; leave a file with shell code unchanged after the backup while still generating the other file; verify by updating `test_env_pull_warns_and_keeps_original_when_overlay_would_need_overwrite` and `test_env_pull_keeps_both_files_with_complex_host_content` (no `SystemExit`; carried-over line present; `~/.env.local` unchanged) and adding a test that a carried-over key stays in the section on a second sync
- [x] 2.2 Print one short notice per affected file (keys, file, Bitwarden item, backup path, `run: machine attention`), key names only, no values; verify with a capsys test that the notice contains these parts and no value
- [x] 2.3 In the Readme env section (around "These files are **not** in git"), replace the sentence that local override files are left unchanged and document the local-only section, the choices and `machine attention`; verify the Readme text matches the spec scenarios

## 3. Interactive choices

- [x] 3.1 Decide interactivity with `system.is_tty() and not self.unattended` inside the sync (keeping `interactive=True` from `machine env pull` for the Bitwarden requirement); for each local-only key offer by number via `system.choose`: add to Bitwarden `<item>`, keep locally, remove, skip, with "skip" preselected and the origin hint from 1.2; shell-code files offer keep locally, remove, skip; verify with monkeypatched `system.choose`/`is_tty` tests for each choice and for `--yes` (no prompt, carry-over)
- [x] 3.2 Implement "keep locally": append the line(s) under `# kept from ~/.env on <date>` to `~/.env.local` (create with mode 600 if missing, never rewrite existing content) and drop them from the generated file; verify the existing `~/.env.local` content is a prefix of the new content and the mode is 600
- [x] 3.3 Implement "remove": drop the key from the generated file only; verify the key is absent from both files and present in the backup
- [x] 3.4 Implement "add to Bitwarden": group the chosen lines per item, `bw sync`, read the item with `bw_get_item_raw`, append `# added from <host> on <date>` plus the lines to the notes, write with `bw_edit_item`, then regenerate both files; on unlock or write failure treat the keys as skipped and report it; verify with the `fake_bw` fixture that the notes end with the comment and lines, the regenerated `~/.env` sets the key outside the local-only section, and a failing edit leaves the key in the local-only section

## 4. Callers and attention

- [x] 4.1 Make sure `machine update` (`machine_cli/updates.py`) and `machine setup` (`machine_cli/commands.py`) continue after the env sync with unresolved keys, so `check_ssh_key_backup` and the update-state write still run; verify with a test in `tests/unit/test_update_and_env.py` that an update with a local-only key ends in state `updated` and calls the SSH-key check
- [x] 4.2 Add an env item to `attention_items()` in `machine_cli/attention.py`, derived live from the files (local-only section or shell code), whose resolve step offers the choices of 3.1 and then runs the sync; verify with attention tests that the item is listed with file and keys, is listed without prompting when not on a terminal, and disappears after all keys are resolved

## 5. Validation

- [x] 5.1 Run `pytest tests/unit/test_update_and_env.py tests/unit/test_bw_and_answers.py -q` plus the attention tests; then `pytest tests/unit -q`, because `cmd_env_pull` is shared by `update`, `setup` and `attention`; record commands and results here
  - Result: `pytest tests/unit/test_update_and_env.py tests/unit/test_bw_and_answers.py -q` → 146 passed (includes the attention tests); `pytest tests/unit -q` → 722 passed. The full suite covers every caller of `cmd_env_pull` (`update`, `setup`, `attention`).
- [x] 5.2 Run `pre-commit run --files` on all changed and added paths (including this change directory); record the result
  - Result: `pre-commit run --files` on all changed and new paths → all hooks pass, after black reformatted two files and flake8 E203 in `display()` was fixed.
- [x] 5.3 Manual check on this host in the worktree: run the worktree's `machine_cli/machine env pull` with the current `~/.env` (holding `OPENROUTER_API_KEY`), pick "skip", confirm the local-only section and the attention item, then resolve it via the worktree's `machine_cli/machine attention`; this rewrites the live `~/.env`, so ask the owner first; record what was chosen
  - Result (2026-10-30, this laptop): a non-interactive `machine env pull` from the worktree (stdin not a terminal, so the skip path) rebuilt `~/.env` from `env/groups/private` and wrote `OPENROUTER_API_KEY` unchanged into the local-only section; the shell still sets the key, the backup matches the original file, and `machine attention` listed the `[env]` item. The owner then resolved it in a terminal through the worktree's `machine attention` → "add to Bitwarden env/groups/private". This run still used the old preselection, which was later changed to "skip". The line is now in the item's notes under `# added from <host> on 2026-10-30`, `~/.env` has no local-only section, the key is set and `machine attention` reports nothing.

## Workflow follow-up

- Archive the change inside the worktree, then ask the owner before merging the branch into the main clone and before removing the worktree.
