# Design

## Context

This change writes the confirmed architecture down as baseline specs and changes no code. See proposal.md for the motivation. Current code: `bootstrap` runs from an existing checkout (it locates `machine` relative to itself), installs `uv` if missing, and runs `machine setup`; `machine` is a `uv run --script` file with its dependencies declared inline, backed by the `machine_cli` package.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep unclear points and goals visible as investigations.

**Non-Goals:**
- Fixes or improvements.
- Choosing a different dotfile manager.

## Decisions

1. **One shared repository with symlinks.** Chezmoi was selected because its symlink mode supports in-place edits and syncing them to other machines. It is reconsidered only if a clearly better alternative meets those needs.
2. **Ansible for packages and system configuration.** It was selected after comparing alternatives and is readable to the owner. A replacement is worth considering only for a concrete advantage.
3. **`uv` makes the CLI self-contained.** Bootstrap installs `uv` when missing so everything else comes from it.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Bootstrap through `curl | bash`.** Goal: one command on any machine that clones the repository and sets everything up. Today bootstrap needs an existing checkout. Suggestion: add a small remote entry point that clones the repository, then hands over to bootstrap. Why: it removes the manual clone step on a new host.
2. **Python versions.** Goal: support all Python versions up to the latest. Today the range is 3.11 to 3.13, which was limited to avoid unsupported dependency builds. Suggestion: test newer versions in CI and widen the range as dependencies allow. Why: the range should not need hand maintenance on every new release.
3. **Dotfile manager.** Suggestion: list which chezmoi features are really used and compare GNU Stow, yadm and a simple linker for in-place edits and sync. Why: the choice stands unless a clearly better fit exists, and this shows how much of chezmoi is needed.
4. **`install.py` wrapper.** The owner is unsure whether it is still needed (`--update`, `--new-host`, `--ui` map to `machine`; dry-run is unsupported). Suggestion: find out who calls it and remove it if nobody does. Why: a wrapper nobody uses is maintenance with no benefit.
5. **Migration and rollback code.** `machine migrate` and `machine rollback` serve the move from the old root-symlink layout. All hosts are migrated and removal was planned after 2026-10-28 if no issues appear; the owner is unsure. Suggestion: map the code, tests and documentation that depend on it, then remove it. Why: dead code adds risk and test time.
6. **Which `machine` subcommands are essential.** Suggestion: find which subcommands scripts, tests and documentation call and simplify the rest without losing guided setup or safe updates. Why: a smaller CLI is easier to keep correct.

## Risks / Trade-offs

- The specs omit the migrate and rollback code and the `install.py` wrapper, but both still exist; later changes must not remove them silently.

## Open Questions

None beyond the investigations above.
