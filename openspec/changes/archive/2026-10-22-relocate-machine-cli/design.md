# Design

## Context

The CLI package lives in `home/dot_local/lib/machine_cli/` and is deployed by chezmoi in symlink mode, one symlink per file. Executable files such as `executable_machine` are copied, not symlinked, because chezmoi's symlink mode only links plain files. `bootstrap` locates the repository from `BASH_SOURCE[0]` and runs the script inside the checkout, so it only works from a checkout. `machine` already runs `git -C <repo>` for updates. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- A plain `git pull` never leaves `machine` broken or triggers a chezmoi overwrite prompt.
- The checkout location is discovered, not configured, so a clone can be anywhere.
- `curl | bash` bootstrap works for a public repository.

**Non-Goals:**
- Supporting piped bootstrap for a non-public repository (accepted limitation).
- Pulling in bootstrap; `machine update` remains the only updater.
- Changing the chezmoi-managed dotfiles or the `machine/` host data directory.

## Decisions

**CLI outside chezmoi, in `machine_cli/` at the repository root.** The tool that orchestrates chezmoi must not depend on chezmoi having deployed it; otherwise a manual `git pull` can leave it unable to start and unable to repair itself. Alternative considered: keep it in `home/` as a single directory symlink. Rejected: chezmoi would still own the code the update path needs, and the entry-point copy would still prompt. Alternatives not chosen: a self-healing wrapper that runs `chezmoi apply` on import failure, an editable install, documenting `chezmoi apply` after a pull.

**Entry point is a symlink; the repository is found by resolving it.** `~/.local/bin/machine` links to the script in the checkout; resolving it yields the checkout, so no path is stored and any location works. This also covers a manual clone followed by setup. A configured fallback path was not adopted.

**Bootstrap detects piped runs and clones to `~/dotfiles` over HTTPS.** Override with `DOTFILES_DIR`. Existing clones are used as is; no pull, so update safety (local-change handling) stays in `machine update`.

**No dependency step in `machine update`.** The Python dependencies are declared in the script header and resolved by `uv` on every start, so a pulled change to the header takes effect on the next run without an update step. The first run after such a change needs network access to build the environment; the exact `typer` pin keeps this rare. The running update process keeps its old environment until it exits. Tools outside the header (chezmoi, ansible-core, bw) are not covered by this change.

**Existing hosts migrate once.** A chezmoi script, run when chezmoi applies on an updated host, replaces the copied `~/.local/bin/machine` with the symlink; `.chezmoiremove` removes the old deployed package directory. Running `./bootstrap` does the same by hand.

## Risks / Trade-offs

- [A host that pulls by hand before migrating has a broken `machine`] -> run `./bootstrap` or `chezmoi apply` once; the Readme states this.
- [Piped bootstrap fails for a non-public repository] -> accepted limitation.
- [`machine_cli/` next to the `machine/` host-data directory is easy to confuse] -> documented in the Readme.
- [CI, tests and path-based update classification reference the old locations] -> updated in the same change; `machine_cli/` changes still need no extra update step.

## Migration Plan

1. Move the package and entry script; update tests, CI, noxfile, Readme and classification.
2. Add the one-time chezmoi migration script and `.chezmoiremove` entry.
3. Add clone detection and the link step to `bootstrap`.
4. On each host: `machine update` (if it still starts) or `~/dotfiles/bootstrap`. Rollback is `git revert`, then `chezmoi apply`.

## Assumptions

- The entry script sits inside `machine_cli/` (for example `machine_cli/machine`), so resolving the symlink gives the checkout as the parent of the package.
- Running a chezmoi script is acceptable for the one-time migration of existing hosts.
