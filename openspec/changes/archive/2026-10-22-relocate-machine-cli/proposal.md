# Proposal

## Why

A plain `git pull` on a host leaves the `machine` command broken. The CLI package is deployed by chezmoi as one symlink per file, so a module added upstream has no symlink until `chezmoi apply` has run, and `machine update`, the command that would run it, cannot start. The `machine` entry point is also a chezmoi-written copy (chezmoi symlinks only plain files), so chezmoi asks for confirmation before overwriting it after a manual pull.

The tool that orchestrates chezmoi should not depend on chezmoi having deployed it. Bootstrap also only works from an existing checkout, so a new host cannot start with `curl | bash`.

## What Changes

- Move the CLI package from `home/dot_local/lib/machine_cli/` to `machine_cli/` at the repository root, outside chezmoi's source tree.
- `~/.local/bin/machine` becomes a symlink into the checkout, created by bootstrap/setup. The entry point finds the repository by resolving its own symlink, so the checkout can be anywhere and no path is configured.
- `./bootstrap` detects whether it runs from a checkout or piped (`curl | bash`). When piped, it clones the repository over HTTPS (default `~/dotfiles`, overridable) and continues from the clone. The repository is assumed to be public; piped bootstrap does not work otherwise.
- Re-running bootstrap on an existing clone does not pull; it runs `machine setup`. `machine update` stays the only command that updates.
- Existing hosts get a one-time migration (replace the copied entry point with the symlink, remove the old deployed package).
- Update classification, tests, CI and the Readme use the new paths; a change under `machine_cli/` still needs no extra update step (existing `update-flow` requirement, no spec change).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-layout`: the CLI lives outside the chezmoi source tree and is reached through a symlink to the checkout; `./bootstrap` is the entry point both from a checkout and piped.
- `bootstrap`: clone-or-detect behaviour for piped runs, re-run behaviour, entry-point link; `machine` runs from the checkout.

## Impact

- Code: `bootstrap`, `home/dot_local/bin/executable_machine`, `home/dot_local/lib/machine_cli/**`, update classification in `local_changes.py`.
- Tests and CI: `tests/unit`, `tests/integration`, `noxfile.py`, `.github/workflows/verify.yml` reference the old paths.
- Docs: `Readme.md` sections on the CLI layout.
- Profiles: all (work-machine, home-laptop, home-server, rpi, rpi-zero, container); the container launcher (`sdx`) runs `./bootstrap` from a mounted checkout and must keep working.
