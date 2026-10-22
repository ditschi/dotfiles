## Why

The shell configuration under `home/dot_zsh/config/` is one flat folder. It mixes modules that only zsh can load with modules that bash reuses (and that must stay bash-compatible), and it mixes work modules with the rest. The owner suggested during the baseline of `shell-setup` to investigate a clearer structure, for example separate folders for zsh-only, shared and work modules. That suggestion was recorded only as item 3 of `archive/2026-10-21-baseline-shell-setup/design.md`, and the follow-up report (`openspec/investigations/shell-and-prompt.md`, A3 and A4) covered only the cost of moving files, not the classification itself.

This change is an investigation: it collects facts and options for discussion. It does not change code or specs.

## What Changes

- Classify every module in `home/dot_zsh/config/` and the helpers in `home/dot_zsh/` as zsh-only, shared with bash (must stay bash-compatible), or work-only.
- Compare layout options and their effect on loading, on the hard-coded module list in `home/dot_bashrc`, and on the profile-based exclusion in `home/.chezmoiignore`.
- List every consumer of the current paths so a later restructure can be planned.
- Check whether `07_machine.zsh` is sourced twice (once from the zinit `atinit` hook in `02_plugins.zsh`, once by the loader glob).
- Record the owner's decision. A restructure, if wanted, becomes a separate implementation change.

Affected capabilities: `bash-shared-config`, `shell-handoff` (consumers of the paths). Affected profiles: all; the work folder affects `work-machine` only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. If the decision changes behaviour, the implementation change carries the spec deltas.

## Impact

None until a decision is made. Known consumers of the current paths (to verify): `home/dot_bashrc` (bash module list, work gate), `git-credential-env` (loads `01_env.zsh` via `bash -c`), `zsh-handoff-check.sh` (watch list), `home/.chezmoiignore` (work modules), `00_LOADER.zsh` (glob), unit and Docker tests.

## Open Questions

- Should the shared (bash-compatible) modules be recognisable by folder, by file suffix (for example `.sh`), or only by a documented list?
- Would a work folder let the loader and `.chezmoiignore` ignore one directory instead of three file names?
- Should the loading order stay numeric, or become explicit stages per folder?
- Is a restructure worth the migration cost on existing hosts (symlinks in `$HOME`)?

## Initial facts (read from the files, not yet discussed)

- Bash sources from `home/dot_bashrc`: `00_alias`, `01_env`, `05_pyenv`, `06_history`, plus `01_work_tools` and `01_work` when `WORK_SETUP=true`. These are the modules that must stay bash-compatible.
- Zsh-only by use: `02_plugins`, `03_theme`, `04_keybindings`, `07_machine` (zinit hook), `08_node`, and `01_work_ldap_helpers` (not loaded by bash).
- Work modules (`01_work*`, three files) are excluded per profile through `home/.chezmoiignore`.
- The zsh loader sources every `*.zsh` in the folder by glob, so a new file is loaded without registration; bash uses a hard-coded list.

## Source material

- `openspec/investigations/shell-and-prompt.md`, sections A3 and A4.
- `openspec/changes/archive/2026-10-21-baseline-shell-setup/design.md`, investigations 3 and 4.
