# Design

## Context

This change writes the confirmed Git configuration down as baseline specs and changes no code. See proposal.md for the motivation. Current code: `home/dot_gitconfig` (shared), `home/create_dot_gitconfig.local.tmpl` (host-local), `home/dot_config/git/{private,work}.gitconfig` (identity snippets), `machine/gitconfig.py` (check and move), and the `git_min` Ansible role (ensures Git 2.36 or newer).

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep unclear points visible as investigations.

**Non-Goals:**
- Fixes or improvements.

## Decisions

1. **Owner rules instead of path rules.** Repositories live under different roots on different machines, so the remote owner chooses the identity.
2. **Shared file is a symlink.** Aliases and defaults sync with the dotfiles; everything host-specific goes to the local file.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Credential helper layout.** The identity snippets set `credential.username` and a `git-credential-env` helper per host, with an empty `helper =` first to drop inherited helpers. The owner marked this unclear. Suggestion: list each host and its token variable and confirm which parts are wanted. Why: it decides that tokens never reach `~/.git-credentials`.
2. **Local `credential.helper=store`.** Suggestion: find which hosts and remote types depend on it and test what breaks without it. Why: it may store tokens in plain text, so it should stay only where needed.
3. **`user.useConfigOnly`.** It is set today. Suggestion: describe what happens when no identity rule matches and which workflows rely on it. Why: it decides whether Git guesses an identity or asks for one.
4. **Suspected legacy settings** such as `workdir`. Suggestion: search for references and the tests or workflows that touch them before removing anything. Why: unused settings are clutter, but removal may break something.
