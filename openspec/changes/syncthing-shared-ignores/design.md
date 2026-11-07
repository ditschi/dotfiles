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
  - `ensure_defaults(config, rules)`: sets `<defaults><ignores>` to the rule list (while Syncthing runs: `PUT /rest/config/defaults/ignores`, see Verified with Syncthing v2.1.5).
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

- [`#include` of a file that does not exist yet puts the folder into an error state] → Verified with Syncthing v2.1.5 (see Verified with Syncthing v2.1.5). The include line is therefore added only when `.stglobalignore` exists (Open Question 1).
- [Syncthing rewrites `config.xml` while it runs and may drop a direct edit] → Use `PUT /rest/config/defaults/ignores` of the running instance (verified in task 1.1).
- [The rule list in the repository and a folder's `.stglobalignore` drift apart] → The repository copy only seeds new folders; the synced file wins for existing ones, because its rules come first.
- [`(?d)` lets Syncthing delete ignored build output when it blocks a directory deletion] → Build output is rebuilt locally, so losing it costs a rebuild only.

## Migration Plan

On the first `machine apply` or `machine update` after the change, each host with the feature gets the include line in every folder's `.stignore` and the default ignore patterns. Rollback: revert the change; the include lines stay and are harmless, and the owner removes them by hand if wanted. Hosts without the dotfiles are set up by hand once, as described in `docs/features.md`.

## Verified with Syncthing v2.1.5 (task 1.1, 2026-11-07)

Checked on ThinkPad-L13-Yoga-Gen-2 with the installed Syncthing v2.1.5. The tests ran in a separate throwaway instance (own home directory under the session scratchpad, GUI on 127.0.0.1:18384, listening only on localhost, no discovery and no relays). The live instance was only read, not changed.

- **Live instance on the L13:** Syncthing runs as the login user `ditschi`, started from the GNOME session (scope `app-gnome-syncthing-restart.scope`); the packaged `syncthing.service` user unit is disabled. `syncthing paths` prints the configuration file `~/.config/syncthing/config.xml` and the database `~/.local/state/syncthing/index-v2`, so configuration and data are in different directories (Open Question 8). The GUI and REST API listen on `127.0.0.1:8384` without TLS.
- **Folders on the L13:** "ALL Photos" (`/home/family/photo`), "ALL Documents" (`/home/family/documents`) and "Photo Sync Ditschi" (`/home/family/photo/_Photo_Sync_Ditschi`). All three paths are writable by `ditschi`; `/home/family` belongs to `ditschi`, group `family` (Open Question 9). Only "ALL Documents" has a `.stglobalignore`, and its `.stignore` already starts with `#include .stglobalignore`. The `.stignore` of "ALL Photos" is an allow list: `!` lines followed by `(?d)*`.
- **Current `.stglobalignore` of "ALL Documents":** it differs from the initial content above by an opt-in exception `!/DIY/uCPU und Elektronik/ext_resources/**` above the rules (vendored micropython/btstack sources contain a source directory named `target`).
- **Current default ignore patterns on the L13:** `<defaults><ignores>` already holds four lines: `(?d)@eaDir`, `(?d)#recycle`, `(?d)#snapshot`, `__*` (Open Question 10).
- **Missing include target:** a `.stignore` with `#include .stglobalignore` and no such file puts the folder into the state `error` ("loading ignores: parse error: failed to load include file .stglobalignore: file not found"); `/rest/db/ignores` returns an empty `expanded` list. Once the file exists, the next scan clears the error. Not tested: whether a folder in this state still receives files from a peer. A folder in an error state does not sync, so a new device could probably never receive the `.stglobalignore` that would clear the error.
- **Default ignore patterns while Syncthing runs:** `GET` and `PUT /rest/config/defaults/ignores` with body `{"lines": [...]}` (header `X-API-Key`; key and GUI address come from `config.xml`). `PUT` returned 200, and Syncthing wrote the lines to `<defaults><ignores>` in `config.xml` itself. The CLI offers the same as `syncthing cli config defaults ignores`.
- **Default ignores and new folders:** a folder added through `POST /rest/config/folders` did not get the default ignore patterns; no `.stignore` was written. The default patterns are applied by the web GUI when it adds or accepts a folder (from Syncthing's documentation, not tested here).
- **Reloading `.stignore`:** `GET /rest/db/ignores` read a changed `.stignore` without a rescan. `POST /rest/db/ignores?folder=<id>` with `{"ignore": [...]}` writes `.stignore` and makes the running instance load it at once.

## Assumptions

- ditschi-ThinkPad-T480 has no host config in `machine/hosts/` today; it gets the behaviour only after `machine setup` on it selects the feature `syncthing`.
- On other hosts with the feature, Syncthing also runs as the login user that runs `machine`, as verified on the L13.

## Open Questions

1. **`#include` of a missing file.** Tested in task 1.1: the folder goes into an error state until the file exists (see Verified with Syncthing v2.1.5). Recommended: add the include line only when `.stglobalignore` exists, and report the folder as waiting otherwise. On the L13 that means "ALL Photos" and "Photo Sync Ditschi" wait until a `.stglobalignore` is created there.
2. **May the dotfiles create `.stglobalignore` when it is absent?** Recommended: no. Creating it on two devices before they have synced would produce conflict files, and the NAS is the owner's place to create it. Alternative: create it from the repository rule list only when the folder has no `.stglobalignore` and none of its peers has one, which `machine` cannot know reliably.
3. **`.claude/worktrees`.** The owner decided not to ignore them for now because they may hold uncommitted work. Should they be revisited later, for example with an ignore for their build output only (already covered by `**/target` etc.)?
4. **Servers.** Should the feature `syncthing` stay excluded on servers? This change keeps the exclusion; a server running Syncthing would be set up by hand.
5. **Trigger.** Recommended: a `machine` step (`syncthing ignores`) in `setup`, `apply` and `update`, because the work is per user, needs no root, and sits next to the other per-feature user steps; `machine update` also runs in the background job, so new folders are wired up without a manual run. Alternatives:
   - An Ansible role with `when: "'syncthing' in machine_features"`: Ansible runs as root and is skipped on hosts with `ansible: false`; it would have to switch to the login user.
   - A systemd user unit in a dotfile group (path unit on `config.xml`, or a timer): reacts faster to a newly accepted folder, but adds a unit and a script outside `machine`, and needs its own tests.
6. **Where the rule list lives.** Recommended: one copy in the repository, used only for the default ignore patterns. Alternative: read the rules from an existing `.stglobalignore` of a chosen folder (for example "ALL Documents"), so that there is no second copy; this ties the defaults to one folder being present on every host.
7. **Default ignore patterns content.** Should `<defaults><ignores>` hold only the rules, or `#include .stglobalignore` followed by the rules? Because of question 1, an include line in the defaults would put every newly accepted folder into an error state. Recommended: the rules only; the step adds the include line on its next run, once `.stglobalignore` has arrived.
8. **Order of the configuration directories.** When both `~/.local/state/syncthing/config.xml` and `~/.config/syncthing/config.xml` exist, which one is live? Verified: `syncthing paths` prints the live configuration file (on the L13 `~/.config/syncthing/config.xml`, while the database is under `~/.local/state/syncthing`). Recommended: use `syncthing paths`, and fall back to the first existing file of `~/.local/state/syncthing` and `~/.config/syncthing` only when the command fails.
9. **Folders of another user.** Verified: on the L13 Syncthing runs as `ditschi`, and all three folders under `/home/family` are writable by `ditschi`. Recommended: handle only the login user's own Syncthing instance, folders outside the home directory included; folders it cannot write are reported and skipped.
10. **Existing default ignore patterns.** `<defaults><ignores>` on the L13 already holds `(?d)@eaDir`, `(?d)#recycle`, `(?d)#snapshot`, `__*` (Synology folders and the owner's `__` convention). Should the step replace the defaults with the shared rules, or put the shared rules first and keep the existing lines below them? Recommended: shared rules first, existing lines kept below them, no duplicates. That way the step adds lines and never removes the owner's own ones.
