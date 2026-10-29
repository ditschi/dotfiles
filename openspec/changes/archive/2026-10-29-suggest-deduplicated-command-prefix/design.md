# Design

## Context

See proposal.md for the requested workflow. zsh currently implements pasted prompt cleanup in `home/core/.zsh/config/04_keybindings.zsh` with a dollar alias and a prompt-character function. Bash implements the corresponding helpers in `home/core/.bashrc`, including a command-not-found handler for the dollar case. Neither currently deduplicates failed commands.

zsh has existing precmd hooks in `03_theme.zsh`. Bash constructs PROMPT_COMMAND before initializing Starship; mise, history synchronization and dotfile update hooks already participate. The archived adopt-antidote-starship design records why bash keeps the existing line editor and the importance of retaining mise's prompt hook. Existing shell regression tests live in `tests/unit/test_zsh_handoff.py`; they include subprocess and PTY patterns.

## Goals / Non-Goals

**Goals:** Offer a correction after the original failure, in the shell's editable command line, without running it automatically.

**Non-Goals:** Rewrite successful commands, add a general typo corrector, change the existing pasted prompt helpers, or introduce a line-editor replacement.

## Decisions

The original command runs first. Duplicate-prefix cleanup is considered only after failure. The owner selected placing the cleaned command at the prompt for confirmation rather than automatically retrying it, after the risk of repeating side effects was raised.

Both single-word and multiword prefixes are covered: `git git status` becomes `git status`, and `git remote git remote -v` becomes `git remote -v`.

## Assumptions

The following implementation details are proposed, not additional owner-confirmed decisions:

- Use one small bash/zsh-compatible helper under `home/core/.zsh/` for literal-word matching, sourced by the two interactive integrations. Do not evaluate the text, expand substitutions or resolve aliases to detect duplicates.
- Initially accept only single-line commands made of unquoted literal words separated by whitespace. Reject quotes, escapes, expansions, redirections, pipelines, command lists and other shell syntax conservatively. This avoids changing the meaning of a command while reconstructing it.
- Compare complete leading word sequences; select the longest adjacent repeated prefix and remove its first copy once. Leave the remaining original text intact, rather than normalizing the whole command. Embedded repetition and partial-word duplication are not matches.
- In zsh, capture the submitted line with a preexec hook and consume its exit status at the start of precmd. Stage one pending suggestion and insert it through a composable line-init widget only when the editor is empty and no user input is queued. Preserve existing widgets and prompt hooks.
- In bash, use a small wrapper around the existing accept-line binding to capture the complete Readline line without executing it or modifying it. At the first prompt hook, capture the prior status and derive a pending suggestion. Arrange a one-shot Readline insertion using native bindings, preserving existing keymaps and bindings. Restore ordinary acceptance afterward. Test PTY behavior with both Starship and the fallback prompt; do not use a DEBUG trap that captures individual internal commands instead of the submitted line.
- Preserve the failed status for Starship and subsequent prompt hooks. Keep the original history entry; only a suggestion submitted by the user becomes a second entry. Clear stale state on each submission and consume a pending suggestion at most once.
- No changes to non-interactive shells or additional runtime packages are needed. Both shells receive the helper across existing work and private profiles.

## Risks / Trade-offs

- Failed commands can already have side effects. Confirmation avoids an unsolicited second execution, but cannot undo the original command.
- Prompt hooks may clobber exit status or run more than once. Capture status before other hooks and test a side-effect marker proving that only the original command runs before confirmation.
- Readline insertion can conflict with keymaps or queued typing. Verify real PTY interaction, preserve existing bindings and prefer no suggestion over replacing user input.
- Conservative syntax filtering leaves some paste errors uncorrected. Keep those commands unchanged instead of evaluating text to guess their meaning.
- Existing zsh spelling correction can intervene before command execution. Preserve it and isolate duplicate-prefix regression tests from spelling prompts.

## Migration Plan

Implement and test the helper and integrations, then document the behavior in Readme.md. Normal dotfile application and opening a fresh interactive shell enable it. Removing the helper integrations and opening a new shell restores prior behavior; no persistent suggestion state or migration is planned.
