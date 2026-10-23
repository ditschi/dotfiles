# Proposal

## Why

Slim down the `machine` CLI: less hand-written logic and fewer private-API workarounds, so it is easier to maintain.

## What Changes

- Replace the shell-completion workarounds in the `machine` script (private `typer` modules, an exact `typer==0.27.2` pin, patched completion classes) with a CLI toolkit that supports bash and zsh completion natively. The toolkit is chosen in the design; the hand-written prompt helpers (`choose`, `choose_many`, `prompt_yes_no`) move to the same toolkit.
- Split `machine_cli/bitwarden.py` (722 lines, one mixin) into a small `bw` client wrapper, the `env pull` logic and the SSH-key logic, and remove setup code that turns out to be redundant. `bw` stays the only Bitwarden tool; `rbw` is recorded in `openspec/backlog.md` for later.
- Replace the separate local-change resolvers (`machine/gitconfig.py`, `.bashrc` block relocation in `local_changes.py`) with one generic helper that moves host-local additions from shared files into `.local` files, using marker comments.
- Add a small local event log (append-only JSON Lines in the state dir) that counts update outcomes, including how often the automatic revert is used, so later cleanup decisions rest on data.
- **BREAKING** (CLI internals only): the `*Mixin` classes and module layout of `machine_cli/` change; the commands and their options stay the same.

## Capabilities

### New Capabilities
- `local-overrides`: how host-local additions (for example externally managed blocks) are detected in shared dotfiles, listed, and moved into `.local` files using marker comments; re-appearing text is removed again and diverging text is reported and resolved interactively.

- `machine-events`: host-local, best-effort event log of update and helper outcomes; no secrets, no network.

### Modified Capabilities
- `update-flow`: the local-change resolvers are replaced by the `local-overrides` helper. The rest of the update-flow simplification (file difference, upstream tip, relevance filter, one state file, attention entry point) is part of `adopt-mise`.
- `git-config`: host-only keys are handled by the `local-overrides` helper and an `[include]` of `~/.gitconfig.local` instead of `machine/gitconfig.py`; an equal value is moved, a different value is a conflict the user resolves.

Affected profiles: all. Work machines are affected most, because they receive externally managed additions; the change must keep working without root.

## Impact

- Code: `machine_cli/` (all modules), the `machine` script, `machine/gitconfig.py`, `tests/unit/`, `.pre-commit-config.yaml` and `.github/workflows/verify.yml` (the `gitconfig.py --check` entries).
- Dependencies: the CLI toolkit and its pin in the `machine` script's inline `uv` metadata.
- Specs: `update-flow`, `git-config`, new `local-overrides`. `bash-shared-config` and `zsh-config-loading` (completion, managed blocks) keep their requirements.
- Related changes: `adopt-mise` (tools, dotfile groups and the update-flow simplification) builds on this change and is archived after it. It reuses the toolkit and the helper's conflicts, and adds `machine attention`.
