# Design

## Context

This change writes the confirmed env and secret behaviour down as baseline specs and changes no code. See proposal.md for the motivation. Current code: the loader is `home/dot_zsh/config/01_env.zsh`, generation and Bitwarden handling are in `machine_cli/bitwarden.py`, and the helpers are `git-credential-env` and `get-password` in `home/dot_local/bin`.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep unclear points and gaps visible as investigations.

**Non-Goals:**
- Fixes or improvements.
- Choosing a different secret manager (the owner dropped that comparison).

## Decisions

1. **Plain `KEY=value` is the preferred env format.** The `export` form is supported too. Plain files work for Docker Compose environment files.
2. **Three fixed files with layers.** Generated shared and host files are separate from a local file that keeps local settings private.
3. **`bw` goes to `~/.local/bin`.** The path was chosen automatically without a recorded reason; the owner accepts it.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Load order.** The current order is accepted, but no reasoning was done. Suggestion: check whether another order or a per-variable rule fits better. Why: the order decides which file wins.
2. **Flexible env file locations.** Not supported today and may become a feature. Suggestion: collect concrete cases first, such as per-project files. Why: avoid building flexibility nobody uses.
3. **Permission handling.** Today a too-open file only gets a warning with the `chmod` hint. Expected: warn, tell the user that the permissions were fixed, and fix them. Suggestion: decide whether the loader changes the mode itself or only the pull command does. Why: a silent change would surprise users, and an open secret file is a risk.
4. **`git-credential-env`.** The owner is unsure about its behaviour, including the fallback to loading `01_env.zsh` in a bash subshell. Suggestion: list who calls it and in which environments, then confirm each path. Why: the fallback runs shell code from a credential helper.
5. **`get-password`.** Today it uses the GNOME keyring (`secret-tool`) and falls back to `$PASSWORD`. Goal: use Bitwarden when it is set up, and define how a secret with a password depends on user or profile. Suggestion: add Bitwarden as the first source and look up an item name derived from profile. Why: one source of passwords across machines.
