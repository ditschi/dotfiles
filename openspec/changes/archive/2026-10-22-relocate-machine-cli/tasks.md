# Tasks

Assumption carried from design.md: the entry script lives at `machine_cli/machine`.

## 1. Move the CLI out of chezmoi

- [x] 1.1 `git mv` the package to `machine_cli/` and the entry script to `machine_cli/machine`; the script finds the package from its resolved path. Verify `python3 machine_cli/machine --help` works from the checkout.
- [x] 1.2 Update `classify_paths` and its unit tests so changes under `machine_cli/` need no extra step. Verify `pytest tests/unit -q` passes.
- [x] 1.3 Point `tests/unit`, `tests/integration`, `noxfile.py` and `.github/workflows/verify.yml` at the new paths. Verify `pytest tests/unit -q` and `nox` compile sessions pass.
- [x] 1.4 Add a unit test that a symlink to the script from an arbitrary directory resolves the checkout and imports the package. Verify it passes.

## 2. Bootstrap

- [x] 2.1 Detect checkout vs piped run; piped clones over HTTPS to `${DOTFILES_DIR:-$HOME/dotfiles}`, uses an existing clone without pulling, and stops with a clear message when `git` is missing. Verify with a piped run in a container (`curl | bash` style) and a run from a checkout.
- [x] 2.2 Link `~/.local/bin/machine` to the checkout's script, replacing a regular file. Verify in a test that a regular file is replaced by a symlink and a re-run is idempotent.
- [x] 2.3 Confirm `sdx` extended mode still works with the mounted checkout. Verify `bootstrap --profile container --yes --no-become` runs in the Docker test.

## 3. Migrate existing hosts

- [x] 3.1 Add the chezmoi script that replaces the copied `~/.local/bin/machine` with the symlink and the `.chezmoiremove` entry for the old deployed package. Verify on a host or container with the old layout that `chezmoi apply` leaves a working `machine` and no prompt appears.
- [x] 3.2 Verify a plain `git pull` that adds a CLI module on a migrated host leaves `machine update` working without `chezmoi apply`.

## 4. Docs and checks

- [x] 4.1 Update the Readme CLI layout, bootstrap (`curl | bash`, `DOTFILES_DIR`) and the one-time migration note. Verify the documented commands run as written.
- [x] 4.2 Run `pre-commit run --all-files` and `pytest tests/unit -q`; run the Docker/APT tests per Readme "Tests".

## Workflow follow-up

- Archive the change after review, so `repo-layout` and `bootstrap` receive the deltas.
