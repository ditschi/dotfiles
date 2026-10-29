# Tasks

## 1. Literal duplicate-prefix matching

- [x] 1.1 Add a small shared bash/zsh-compatible helper under `home/core/.zsh/` using the matching assumptions in design.md. Add focused subprocess tests in `tests/unit/test_command_prefix.py`, following the shell invocation patterns in `test_zsh_handoff.py`; verify both shells handle single-word and multiword prefixes, longest matches, whitespace, no match, embedded repetition and partial words without evaluating text.
- [x] 1.2 Cover conservative rejection of quotes, escapes, expansions, redirections, pipelines, command lists and multiline input in the same tests. Verify marker commands embedded in rejected input never run and document the literal-word boundary in the helper's test cases.

## 2. Interactive shell integration

- [x] 2.1 Integrate zsh submission capture, failure detection and one-shot editable insertion alongside `04_keybindings.zsh`, preserving existing prompt hooks and widgets. Extend the focused test module with PTY checks proving the original command runs once, failure offers the cleaned line, success offers nothing, and editing, cancellation and explicit submission work.
- [x] 2.2 Integrate the same workflow in `home/core/.bashrc` using native Readline and prompt hooks without a line-editor replacement. Verify the same PTY cases in bash, including existing keymaps, both carriage-return and newline acceptance, and the Starship and fallback prompt paths.
- [x] 2.3 Add regression cases for original exit status, history, no stale suggestions, queued input, existing editor text, non-interactive shells and existing pasted prompt/sudo helpers. Verify `pytest tests/unit/test_command_prefix.py tests/unit/test_zsh_handoff.py -q` passes and side-effect markers remain unchanged until explicit confirmation.
- [x] 2.4 Update the shell section of `Readme.md` with the failure-only, editable suggestion workflow and literal-word limitation; verify documented single-word and multiword examples in fresh interactive zsh and bash sessions.

## 3. Integration validation

- [x] 3.1 Run `pre-commit run --all-files` and `pytest tests/unit -q`; verify both pass without unrelated edits. No Ansible validation is required because no Ansible files change.
- [x] 3.2 Run `openspec validate suggest-deduplicated-command-prefix --strict` and verify the implementation satisfies both capability delta scenarios before marking the change complete.

Validation status (2026-10-29): `pytest tests/unit -q` passes (565 tests, 191 deprecation warnings); `pre-commit run --all-files`, pre-commit checks for the new files, the 176 focused shell tests, and `openspec validate suggest-deduplicated-command-prefix --strict` all pass.
