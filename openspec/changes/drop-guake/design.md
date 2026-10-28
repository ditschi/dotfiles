# Design

## Context

See proposal.md for the motivation. State checked on 2026-10-28:

- `packages_by_feature.gnome` in `ansible/group_vars/all/packages.yml` lists `guake`; the help text of `gnome` names it. The spec `user-tools` says "Guake SHALL stay installed" (from the archived change `add-ddterm-gnome-extension`, which kept Guake next to Ddterm and left Ddterm settings for later).
- `machine_cli/terminal_fonts.py` sets the Guake font through `gsettings` (`guake.style.font style`, size kept) and the VS Code terminal font; `MiseToolsMixin.run_tools_install` calls `set_terminal_fonts()` for the feature `fonts`, before `ensure_gnome_extensions()`.
- Ddterm 64 keeps its settings in the schema `org.gnome.shell.extensions.ddterm`, path `/com/github/amezin/ddterm/`, compiled in the extension directory (`~/.local/share/gnome-shell/extensions/ddterm@amezin.github.com/schemas`), not in the system schema directory. The font keys are `use-system-font` (default `true`) and `custom-font` (default `'Monospace Regular 10'`, a Pango font description).
- Tests that name Guake: `tests/unit/test_terminal_fonts.py`, `tests/unit/test_package_presets.py`, `tests/integration/test_host_yaml_install.py`.

## Goals / Non-Goals

**Goals:**
- Hosts with `gnome` no longer get Guake, and the repository has no Guake setup left.
- Ddterm gets the Nerd Font in the first run that installs it.

**Non-Goals:**
- Removing Guake from hosts that have it (owner decision).
- Other Ddterm settings (theme, size, keybindings).
- Removing Guake's leftover user settings (dconf, autostart) on hosts.

## Decisions

**Guake is dropped from the package table, not uninstalled (owner decision).** Ansible no longer lists `guake`, so a removed Guake stays removed and an installed one stays. Actively uninstalling it was offered and not chosen.

**The Guake font code is replaced by a Ddterm font step (owner decision).** Keeping the Guake font code was offered and not chosen; the owner wants no Guake setup logic anywhere. `terminal_fonts` gets `ddterm_font(current)` (keeps the size from the current Pango description, default 10, like `guake_font` did) and `set_ddterm_font(home)`, which calls `gsettings --schemadir <extension>/schemas` to read `custom-font`, then sets `custom-font` and `use-system-font false` only when a value differs. Without the extension's schema directory it does nothing. Going through `gsettings` with the extension's schema keeps the key types checked by the schema; writing raw keys with `dconf` would not.

**The Ddterm font is set after the extension step.** `run_tools_install` calls `set_terminal_fonts()` before `ensure_gnome_extensions()`. The Ddterm font step runs after the extension step instead (VS Code stays where it is), so a first setup installs Ddterm and sets its font in the same run.

## Risks / Trade-offs

- [A Ddterm release renames the font keys or moves the schema] → `set_ddterm_font` reads the key first and logs and skips when the read fails, so the run continues; the unit tests pin the commands.
- [The owner changes the Ddterm font by hand] → the next run sets the Nerd Font again, but keeps the size. This matches the old Guake and VS Code behaviour.
- [Hosts keep a Guake installation that no longer gets updates from the dotfiles] → it still gets Ubuntu updates through apt; removing it is left to the owner.
