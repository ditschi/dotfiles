# Design

## Context

See proposal.md - Why. Current state on `main`:

- `detect_repo()` in `machine_cli/system.py` checks `DOTFILES_REPO`, then the checkout around its own (resolved) script, then `~/dotfiles`. A `DOTFILES_REPO` that is not a checkout prints a warning on every call.
- `home/core/.shell/common/aliases.sh` exports `DOTFILES_REPO=${DOTFILES_REPO:-$HOME/dotfiles}` in every shell, so the shell's default overrides the script location.
- `dotfiles-update-check-job` uses `${DOTFILES_REPO:-$HOME/dotfiles}` and exits 0 when that is not a checkout; the systemd unit does not set `DOTFILES_REPO`.
- `bootstrap` links `~/.local/bin/machine` to `<checkout>/machine_cli/machine`; that link is what the repo-layout spec names as the source of truth.
- The integration containers mount the repository at `/dotfiles` and set `DOTFILES_REPO=/dotfiles` on the container, which hides the shell default.
- The agent rule in `openspec/config.yaml` and `AGENTS.md` calls the checkout "whose path has no `/.worktrees/`" the live one.

## Goals / Non-Goals

**Goals:**
- One source of truth for the live checkout: the `~/.local/bin/machine` link.
- A plain, stable command agents and scripts can call to get it.
- Shell, `machine` and the background job agree on the checkout when it is not at `~/dotfiles`.

**Non-Goals:**
- Moving an existing checkout or changing where piped bootstrap clones by default.
- A flag that answers "is the current directory live"; agents compare paths themselves.
- Changing how worktrees are merged or removed.

## Decisions

### `machine repo` reads the link, not its own location
`machine repo` resolves `~/.local/bin/machine` and prints the checkout two levels above the target (`<checkout>/machine_cli/machine`), after checking that it is a checkout (`.git` and `home/` exist). It ignores `DOTFILES_REPO` and the location of the script that runs it, so `./machine_cli/machine repo` in any worktree still prints the live checkout. Output is one line on stdout, nothing else; errors go to stderr with exit status 1.

Alternatives: parsing `machine status` (rejected: formatted for people, changes over time, slow because it computes the update plan); telling agents to run `readlink -f ~/.local/bin/machine` and strip the suffix (rejected: puts the internal layout into agent rules and is not testable as a contract); the Git common directory (rejected: names the main worktree of a repository, which is wrong for a second independent clone and when the link points elsewhere).

### `machine repo` has no side effects
The `machine` group callback records the disk state and a usage event for most commands. `repo` is excluded from both, like `completion`, so agents can call it as often as needed.

### Path in `machine status`
The `repo` line starts with the path of the checkout `machine` operates on (from `detect_repo()`), home shortened to `~`, followed by the branch and update position. People see the path where they already look; agents use `machine repo`.

### Shell default derived from the link
`aliases.sh` keeps an explicitly set `DOTFILES_REPO`. Otherwise it resolves `~/.local/bin/machine` and, if that points into a checkout, exports that checkout; otherwise it falls back to `$HOME/dotfiles` (still the clone target of `dotfiles-setup` on a host without the link). The derivation is plain POSIX/bash shell with `readlink -f`, because the file is sourced by bash and zsh. Not exporting `DOTFILES_REPO` at all was considered and rejected by the owner in favour of a correct default.

### Background job uses the same rule
`dotfiles-update-check-job` derives `repo` the same way (explicit `DOTFILES_REPO`, then the link, then `~/dotfiles`). It already prefers `~/.local/bin/machine`; the change only fixes the early `exit 0` and the fallback-only path.

### Repository detection order in `machine`
`detect_repo()`: explicit `DOTFILES_REPO` → checkout around the resolved script → checkout the link points into → `~/dotfiles`. The link step only matters when `machine` runs from a copy outside any checkout; it makes the fallback to `~/dotfiles` a last resort.

### Agent rule
`openspec/config.yaml` ("Where to work", apply guidance, proposal rule) and `AGENTS.md` change to:
- The live checkout is the output of `machine repo`. The current checkout is live when `git rev-parse --show-toplevel` equals it.
- New worktrees are created with an absolute path: `git worktree add "$(machine repo)/.worktrees/<change-name>" -b <change-name>`.
- A checkout that is not live (any linked worktree or other clone) is not live regardless of its path; work there and never create another worktree from it.
- When `machine repo` fails, no checkout on the host is live.

### Integration test
A container is started without `DOTFILES_REPO` (new conftest option), with the repository mounted at `/dotfiles` and a stale decoy checkout at `~/dotfiles` (a `git init` with a `home/` directory). Bootstrap runs from `/dotfiles`. The test checks that `machine repo` prints `/dotfiles`, that an interactive zsh and bash export `DOTFILES_REPO=/dotfiles` and print nothing on stderr, that `machine status` names `/dotfiles` and no `DOTFILES_REPO` warning, and that `dotfiles-update-check-job` resolves `/dotfiles` (with `machine` stubbed or `--check` only, so the test stays offline). A real `git clone` into the container was rejected because it would test only committed state.

## Risks / Trade-offs

- [A shell started before the link changed keeps the old `DOTFILES_REPO`, and `machine` treats an inherited value as explicit] → Re-bootstrapping into another checkout is rare; a new login shell picks up the new link. `machine repo` itself is unaffected.
- [`readlink -f` costs one process per shell start] → Negligible next to the rest of the shell startup; only runs when `DOTFILES_REPO` is unset.
- [Agents in an environment without `machine` (CI, plain containers) get exit status 1] → The rule says no checkout is live then, which matches those environments.

## Migration Plan

No migration. After merging, existing hosts pick up the new shell default on the next shell start and the job on its next run; hosts with the checkout at `~/dotfiles` see no change except the path in `machine status`. Rollback is reverting the branch.
