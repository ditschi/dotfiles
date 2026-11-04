# Design

## Context

See proposal.md for the motivation and specs/syncthing-ignores/spec.md for the required behaviour.

Today the feature `syncthing` (`ansible/group_vars/all/features.yml`, help "Syncthing package") only installs the apt package `syncthing` (`packages_by_feature.syncthing` in `ansible/group_vars/all/packages.yml`). It selects no dotfile group and no role. It is preselected on private desktops and excluded for work, on servers and in containers (spec `feature-selection`, "Features of the private infrastructure").

Relevant repository structure:

- `machine` orchestrates; mise applies dotfile groups and user tools without root; Ansible handles apt, `/etc` and system services, and runs with `become: true` (`docs/architecture.md`, "Layers").
- Per-user, per-feature setup that needs no root already lives in `machine`: the `tool install` step (`MiseToolsMixin.run_tools_install` in `machine_cli/mise_tools.py`) reads the applied host features with `features.split(...)` and then installs GNOME extensions (feature `gnome`), downloads the Thunderbird bridge extension (feature `thunderbird`) and sets terminal fonts (feature `fonts`). Its tests in `tests/unit/test_mise_tools.py` replace `system.run` and `system.have` and use a temporary `HOME`.
- `machine setup` and `machine update` run their steps through `steps.Steps` (`machine_cli/commands.py`, `machine_cli/updates.py`); a failing step does not stop the steps that do not need it.
- Dotfile groups under `home/<group>/` are symlinked into `$HOME`. They suit files the repository owns completely; `.stignore` and Syncthing's `config.xml` are owned by Syncthing and the device, so a symlinked file does not fit.

Syncthing behaviour this design relies on (docs.syncthing.net):

- There is no global ignore list for existing folders.
- `.stignore` is never synced. It can `#include` a file inside the folder, and that included file is synced like any other file.
- `<defaults><ignores>` in `config.xml` applies only to new folders (auto-accepted folders or the GUI prefill).
- The first matching pattern wins; `!pattern` re-includes; `(?d)` allows Syncthing to delete ignored files when they block the deletion of a directory.

The laptops run Syncthing v2.1.x. Depending on the version that created the configuration, `config.xml` is in `~/.config/syncthing` or `~/.local/state/syncthing`.

Initial content of `.stglobalignore`, created by the owner on the NAS for "ALL Documents" on 2026-11-04:

```
// Shared Syncthing ignore rules for this folder. This file is synced to every
// device; each device's own .stignore loads it with "#include .stglobalignore".
// Build output and dependency caches: rebuilt locally, never worth syncing.
// To sync one of them anyway, add "!<path>" ABOVE the rules (first match wins).
(?d)**/target
(?d)**/node_modules
(?d)**/.venv
(?d)**/__pycache__
(?d)**/.pytest_cache
(?d)**/.mypy_cache
(?d)**/.ruff_cache
(?d)**/.nox
(?d)**/.tox
```

## Goals / Non-Goals

**Goals:**
- Build output and dependency caches are not synced in any shared folder by default, and are synced only where an explicit exception enables it.
- One place per folder holds the shared rules, and an exception applies on every device at once.
- Hosts with the feature `syncthing` wire up existing folders and new folders without manual steps.

**Non-Goals:**
- Setting up hosts without the dotfiles (Synology NAS, Android phone, Raspberry Pi, family laptops); the owner does that by hand once.
- Writing or maintaining `.stglobalignore` from the dotfiles.
- Changing which hosts get the feature `syncthing`.
- Cleaning up files that were already synced, or shrinking the NAS index database.

## Decisions

1. **One synced `.stglobalignore` per shared folder holds the shared rules.** It lies at the folder root and is synced to every device. Because it is synced, a change to the rules or a new exception reaches every device without touching each one.
2. **Each local `.stignore` loads it with `#include .stglobalignore` as its first line.** The device's own local lines stay below it. Because the first matching pattern wins, a `!` exception in the shared file takes precedence over everything else.
3. **Opt-in exceptions are `!<path>` lines above the rules in `.stglobalignore`.** They apply on every device at once; there are no per-device exceptions for build output.
4. **The dotfiles never write or overwrite `.stglobalignore`.** Its single source of truth is the synced content. Two laptops with different dotfiles versions writing it would create Syncthing conflict files. Whether the dotfiles may create it when it is absent is listed under Open Questions.
5. **The dotfiles handle only hosts with the feature `syncthing`.** Hosts without the feature, or without the dotfiles, are not touched. Rolling the rules out to all such hosts does no harm.
6. **New folders get the shared rules as default ignore patterns.** The dotfiles set Syncthing's `<defaults><ignores>` to the shared rules, so that a folder accepted or added later ignores build output from the start, before its `.stglobalignore` has arrived.
7. **The `#include` line is the only edit to an existing `.stignore`.** When it is missing, it is inserted as the first line; when it is present further down, it is moved to the top. Every other line keeps its content and order.
8. **`.claude/worktrees` is not ignored for now.** Those directories can hold uncommitted work, so syncing them is wanted for the time being. See Open Questions.

## Implementation outline

This outline follows the recommended options in Open Questions; task 0 confirms or changes them before any code is written.

- **Module** `machine_cli/syncthing_ignores.py` with small, pure functions that tests can call directly:
  - `find_config(home) -> Path | None`: the first existing `config.xml` of `~/.local/state/syncthing` and `~/.config/syncthing` (order: Open Questions).
  - `folders(config) -> list[(folder_id, path)]`: the `<folder id=... path=...>` entries, `~` expanded.
  - `with_include(lines) -> lines`: the `.stignore` lines with `#include .stglobalignore` first, no duplicate, other lines unchanged.
  - `ensure_folder(path) -> status`: reads `.stignore` (missing counts as empty), writes it only when `with_include` changed it, never opens `.stglobalignore` for writing, and returns a status (`ok`, `changed`, `skipped: <reason>`).
  - `ensure_defaults(config, rules)`: sets `<defaults><ignores>` to the rule list (how it is written while Syncthing runs: Assumptions).
- **Shared rule list in the repository**: one data file, for example `machine/syncthing/stglobalignore` (or a constant in the module), holding the rules of the initial content above. It is used only for the default ignore patterns, never written into a folder.
- **Step**: a mixin method `run_syncthing_ignores` on `Machine`, run as its own step `syncthing ignores` after `dotfile apply` in `machine setup`/`machine apply` (`machine_cli/commands.py`) and in `_update_steps` (`machine_cli/updates.py`), only when `syncthing` is in the host's features after `features.split(...)`. It logs one line per changed or skipped folder and nothing when everything is already in place. A failure warns and does not fail other steps.
- **Feature table**: help text of `syncthing` becomes, for example, "Syncthing package + shared ignore rules".
- **Docs**: a Syncthing paragraph in `docs/features.md` (scheme, exceptions, manual setup for hosts without the dotfiles); the new module in the table of `docs/architecture.md`.

## Testing

Unit tests in `tests/unit/test_syncthing_ignores.py`, with a temporary `HOME` and a hand-written `config.xml` (the pattern of `tests/unit/test_mise_tools.py`; `system.run` and `system.have` replaced where Syncthing would be called):

- `config.xml` is found in `~/.local/state/syncthing` and in `~/.config/syncthing`; without either, the step does nothing and prints nothing.
- A folder without `.stignore` gets one with the include line only.
- A `.stignore` with local lines gets the include line on top; the local lines keep content and order.
- An include line further down is moved to the top and not duplicated.
- A second run changes no file (content and mtime unchanged).
- `.stglobalignore` is never written: an existing one keeps content and mtime; an absent one stays absent (unless task 0 decides otherwise).
- A folder whose path is missing or not writable is reported and skipped; the other folders are still handled.
- The default ignore patterns equal the repository rule list after the step, and the rest of `config.xml` is unchanged.
- Without the feature `syncthing`, nothing is read or written.
- The step runs in `setup`, `apply` and `update` and a failure in it does not fail the other steps (in the existing step tests of `tests/unit/test_machine_cli.py` or `tests/unit/test_update_and_env.py`).

## Risks / Trade-offs

- [`#include` of a file that does not exist yet may put the folder into an error state] → Untested; see Open Questions. Until it is answered, the recommended behaviour adds the include line only when `.stglobalignore` exists.
- [Syncthing rewrites `config.xml` while it runs and may drop a direct edit] → Use the running instance's interface where it is available; see Assumptions.
- [The rule list in the repository and a folder's `.stglobalignore` drift apart] → The repository copy only seeds new folders; the synced file wins for existing ones, because its rules come first.
- [`(?d)` lets Syncthing delete ignored build output when it blocks a directory deletion] → Build output is rebuilt locally, so losing it costs a rebuild only.

## Migration Plan

On the first `machine apply` or `machine update` after the change, each host with the feature gets the include line in every folder's `.stignore` and the default ignore patterns. Rollback: revert the change; the include lines stay and are harmless, and the owner removes them by hand if wanted. Hosts without the dotfiles are set up by hand once, as described in `docs/features.md`.

## Assumptions

- The laptops' Syncthing runs as the login user that runs `machine`, so `machine` can read its `config.xml` and write each folder's `.stignore`. On ThinkPad-L13-Yoga-Gen-2 the folder path is `/home/family/documents`, so this needs checking (Open Questions).
- ditschi-ThinkPad-T480 has no host config in `machine/hosts/` today; it gets the behaviour only after `machine setup` on it selects the feature `syncthing`.
- While Syncthing runs, the default ignore patterns are written through its REST interface (API key and address from `config.xml`, endpoint for the default ignores) or its command-line interface, and `config.xml` is edited directly only while Syncthing is stopped. The exact endpoint or command for v2.1.x is to be verified in task 1.
- Syncthing picks up a changed `.stignore` on its next scan; the step may additionally ask the running instance to reload the folder's ignores.

## Open Questions

1. **`#include` of a missing file.** What does Syncthing v2.1.x do when `.stignore` includes `.stglobalignore` and that file does not exist yet (for example on a device that has just accepted the folder)? Possibly a folder error; untested. Recommended: test it on a scratch folder in task 0; until it is known, add the include line only when `.stglobalignore` exists and report the folder as waiting.
2. **May the dotfiles create `.stglobalignore` when it is absent?** Recommended: no. Creating it on two devices before they have synced would produce conflict files, and the NAS is the owner's place to create it. Alternative: create it from the repository rule list only when the folder has no `.stglobalignore` and none of its peers has one, which `machine` cannot know reliably.
3. **`.claude/worktrees`.** The owner decided not to ignore them for now because they may hold uncommitted work. Should they be revisited later, for example with an ignore for their build output only (already covered by `**/target` etc.)?
4. **Servers.** Should the feature `syncthing` stay excluded on servers? This change keeps the exclusion; a server running Syncthing would be set up by hand.
5. **Trigger.** Recommended: a `machine` step (`syncthing ignores`) in `setup`, `apply` and `update`, because the work is per user, needs no root, and sits next to the other per-feature user steps; `machine update` also runs in the background job, so new folders are wired up without a manual run. Alternatives:
   - An Ansible role with `when: "'syncthing' in machine_features"`: Ansible runs as root and is skipped on hosts with `ansible: false`; it would have to switch to the login user.
   - A systemd user unit in a dotfile group (path unit on `config.xml`, or a timer): reacts faster to a newly accepted folder, but adds a unit and a script outside `machine`, and needs its own tests.
6. **Where the rule list lives.** Recommended: one copy in the repository, used only for the default ignore patterns. Alternative: read the rules from an existing `.stglobalignore` of a chosen folder (for example "ALL Documents"), so that there is no second copy; this ties the defaults to one folder being present on every host.
7. **Default ignore patterns content.** Should `<defaults><ignores>` hold only the rules, or `#include .stglobalignore` followed by the rules? The answer depends on question 1. Recommended: the rules only; the step adds the include line on its next run.
8. **Order of the configuration directories.** When both `~/.local/state/syncthing/config.xml` and `~/.config/syncthing/config.xml` exist, which one is live? Recommended: ask the installed Syncthing for its paths where it offers that, otherwise prefer `~/.local/state/syncthing`.
9. **Folders of another user.** On ThinkPad-L13-Yoga-Gen-2 the folder is under `/home/family`. Which user runs Syncthing there, and should `machine` touch folders outside the login user's home? Recommended: only the login user's own Syncthing instance; folders it cannot write are reported and skipped.
