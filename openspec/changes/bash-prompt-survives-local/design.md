# Design

## Context

`~/.bashrc` loads the bash modules, with `prompt.bash` last, then sources `~/.bashrc-local` (spec `bash-shared-config`, "Local bash extension point"). `prompt.bash` builds `PROMPT_COMMAND` and then runs `starship init bash`, which makes `PROMPT_COMMAND` call `starship_precmd` and moves the previous value into `STARSHIP_PROMPT_COMMAND`, which `starship_precmd` evals. Starship sets `PS1` on every prompt. A local file that assigns `PROMPT_COMMAND` after that removes the hook, so Starship never runs. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- The Starship prompt works whatever the local file assigns to `PROMPT_COMMAND` or `PS1`.
- Nothing the local file adds to `PROMPT_COMMAND` is lost.

**Non-Goals:**
- Changing where `~/.bashrc-local` is sourced.
- Editing or filtering the content of `~/.bashrc-local`, which is host-only.
- Protecting `PS2` or other variables.

## Decisions

- The hook is repaired after the local file instead of moving the local file before `prompt.bash`. The local file stays the last extension point, as the spec `bash-shared-config` requires (owner decision, 2026-11-09).
- `prompt.bash` defines a function that checks `PROMPT_COMMAND` for `starship_precmd`. If the hook is missing and Starship is initialised, the function appends the current `PROMPT_COMMAND` to `STARSHIP_PROMPT_COMMAND` and sets `PROMPT_COMMAND` back to `starship_precmd`. The chain set up by the repository stays in `STARSHIP_PROMPT_COMMAND`, so the local value runs in addition to it. Running `history -a; history -r` twice is harmless.
- `~/.bashrc` calls the function right after sourcing the local file. When the hook is present, or Starship is not initialised, the function does nothing.
- `PS1` needs no handling, because `starship_precmd` assigns it before every prompt.

Alternatives considered:
- Source `~/.bashrc-local` before `prompt.bash`: simpler, but it contradicts the "at its end" requirement and would let the repository override host-only settings.
- Restore the saved `PROMPT_COMMAND` and drop the local value: loses commands the local file legitimately adds.

## Risks / Trade-offs

- [A local `PROMPT_COMMAND` relies on `$?` of the previous command] → it runs inside `starship_precmd`, which restores the status with `_starship_set_return` before the eval, as for the repository's own chain.
- [Local value duplicates the repository chain] → accepted; the chain is idempotent.
