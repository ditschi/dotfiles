# Tasks

## 1. Stop installing Guake

- [x] 1.1 Remove `guake` from `packages_by_feature.gnome` in `ansible/group_vars/all/packages.yml` and change the `gnome` help text in `ansible/group_vars/all/features.yml` to "GNOME tools (flameshot, shell extensions, …)". Verify that `ansible-lint ansible/*.yml` passes.
- [x] 1.2 Update `tests/unit/test_package_presets.py`: `guake` is in no host's package list. Update `tests/integration/test_host_yaml_install.py`: drop the `guake` assertions (the home laptop checks `flameshot` instead). Verify that `pytest tests/unit -q` passes.

## 2. Ddterm font instead of Guake font

- [x] 2.1 In `machine_cli/terminal_fonts.py`, replace `guake_font`/`set_guake_font` with `ddterm_font(current)` (keeps the size from a Pango description such as `'Monospace Regular 12'`, default 10) and `set_ddterm_font(home)` (only when `~/.local/share/gnome-shell/extensions/ddterm@amezin.github.com/schemas` exists; reads `custom-font` with `gsettings --schemadir`, sets `custom-font` and `use-system-font false` only when they differ; logs and skips when the read fails). Update the module docstring.
- [x] 2.2 In `machine_cli/mise_tools.py`, drop the Guake call from `set_terminal_fonts()` and call `set_ddterm_font` after `ensure_gnome_extensions()` when the host has both `fonts` and `gnome`.
- [x] 2.3 Replace the Guake test in `tests/unit/test_terminal_fonts.py` with tests for `ddterm_font` (size kept, default 10), for `set_ddterm_font` without the schema directory (no command run), with a differing value (both keys set) and with the wanted value already set (nothing written), using a fake `system.run`. Add a test in `tests/unit/test_mise_tools.py` that the Ddterm font is set after the extension step. Verify that `pytest tests/unit -q` passes.

## 3. Docs and checks

- [x] 3.1 Update `Readme.md`: the feature `gnome` no longer names Guake; mention that `fonts` sets the Nerd Font in Ddterm and the VS Code terminal, and that an installed Guake is left alone. Verify that `git grep -n -i guake -- ':!openspec/changes/archive'` finds only this change, the spec text, the Readme note and the negative package test.
- [x] 3.2 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `ansible-lint ansible/*.yml`. All three must pass.
- [x] 3.3 On the owner's host: remove `guake` with apt, run `machine apply` and check that `guake` stays removed; run `machine update` (the font step runs with the tool install, not in `machine apply`) and check that Ddterm shows `FiraCode Nerd Font Mono` in the size it had (`use-system-font` is `false`). Run the font step again and check that nothing is set again.
  Result (2026-10-28): `machine apply` reported `changed=0` and `guake` stayed removed; `machine update` logged "set the Ddterm font to FiraCode Nerd Font Mono 10" (before: `'Monospace Regular 10'`, system font on); `custom-font` is `'FiraCode Nerd Font Mono 10'`, `use-system-font` is `false`, and a second `set_ddterm_font` returned no change.
