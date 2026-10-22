# Design

## Context

This change writes the confirmed project container behaviour down as baseline specs and changes no code. See proposal.md for the motivation. Current code: the wrappers `sde` and `sdx` in `home/dot_zsh/config/01_work.zsh` and the shared launcher `home/dot_local/bin/executable_sde`.

## Goals / Non-Goals

**Goals:**
- Record the confirmed behaviour as requirements.

**Non-Goals:**
- Fixes or improvements.
- Providing the launchers on private machines (the owner does not need them there).

## Decisions

1. **Minimal by default, extended on request.** `sde` stays close to a colleague's environment; `sdx` adds the owner's dotfiles.
2. **Project script wins.** A project that ships its own `.devcontainer/sde.sh` keeps control of how its container starts.
3. **Bash as fallback.** Some containers have no zsh and cannot install it.

## Investigations (not decided, not in the specs)

None. The owner confirmed every point.
