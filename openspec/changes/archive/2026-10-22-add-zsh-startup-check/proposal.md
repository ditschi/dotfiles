# Proposal

## Why

The shell setup prefers zsh with the dotfiles customisation, reached by a handoff from bash. Today that handoff runs unchecked, and nothing tests it. A zsh that fails or starts only partly configured (bare, with poor look and usability) is worse than bash. In that case the shell should stay in bash, tell the user why in one line, and not repeat the check on every start.

Sources (plain text): decision record 0002-shell-setup, investigation INV-0002, the `.bashrc` handoff comment.

## What Changes

- Add a startup health check for the zsh handoff, run from `.bashrc` before `exec zsh`.
- Checks (initial set): zsh is on `PATH` and executable; `zsh -l -i -c exit` succeeds and its stderr is empty; `~/.zshrc` and `~/.zsh/config/00_LOADER.zsh` exist and are readable.
- On failure: do not `exec` zsh, stay in bash, and print one short diagnostic line with the failing check.
- Cache the outcome (pass/fail plus failing check) in a per-user state file under `${XDG_STATE_HOME:-~/.local/state}`; a cached pass skips the check, a cached fail still prints the hint and stays in bash.
- Invalidate the cache and re-check when: any file under `~/.zshrc`, `~/.zsh/config/*.zsh`, `~/.zsh/machine-profile.sh` or `~/.preferred-shell` changes; the zsh binary path or version changes; `~/.dotfiles-update-available` is cleared by `machine update` (dotfiles updated). Manual override: a command to clear the cache and re-run.
- Add a focused unit test for the check, since the handoff has no test coverage today (noted in INV-0002).

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `shell-handoff`: adds a startup health check, a cached result with defined invalidation triggers, and a one-line diagnostic with bash fallback. Depends on `baseline-shell-setup` being archived first.

## Impact

- Code: `home/dot_bashrc` (handoff block), possibly a new bash-compatible helper under `home/dot_zsh/` or `home/dot_local/bin`; `tests/unit/`.
- Decision records: 0002-shell-setup (temporary `docs/decisions/` copy updated while it exists; the durable rationale is in this change's design.md).
- Profiles: all; must work in `container` (Docker skips handoff by default) and on `work-machine` where `chsh` may be unavailable. No root required.
- Startup cost: cache hit must stay cheap (a few `stat` calls, no subprocess spawn beyond what bash already does).

## Open Questions

- Exact value of the hang-guard timeout (design.md suggests about 60 seconds, not yet confirmed).
