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
4. **The dotfiles never overwrite `.stglobalignore`, and create it only when no device has it (owner decision, 2026-11-08).** Its single source of truth is the synced content; two laptops with different dotfiles versions writing it would create Syncthing conflict files. When a folder has no `.stglobalignore`, `machine` asks the running Syncthing whether any known device has announced the file (`GET /rest/db/file?folder=<id>&file=.stglobalignore`, entry `global`). If none has, `machine` creates it from the repository rule list and then adds the include line at once. If a peer has it, or the folder is paused (then the answer says nothing, task 1.2), `machine` waits, and a later run tries again. If it was deleted on another device, `machine` leaves the folder without it and reports nothing, because that is a deliberate choice on that device. When a device accepts an existing folder, the offering device is connected and its index arrives at once, so the file that has not arrived yet is recognised. An extra condition that another device of the folder is connected was considered after task 1.2 and dropped by the owner as not worth the code; the remaining risk is a reported conflict copy.
5. **The dotfiles handle only hosts with the feature `syncthing`.** Hosts without the feature, or without the dotfiles, are not touched. Rolling the rules out to all such hosts does no harm.
6. **New folders get the shared rules as default ignore patterns, without an include line (owner decision, 2026-11-08).** The dotfiles set Syncthing's `<defaults><ignores>` to the repository rule list followed by the host's existing default lines that are not in it (on the L13: `__*`), so that a folder accepted or added later ignores build output from the start. An include line in the defaults would put every new folder into an error state until its `.stglobalignore` arrives (see Verified with Syncthing v2.1.5); `machine update` adds the include line once the file is there.
7. **The `#include` line and `!/.stglobalignore` are the only edits to an existing `.stignore` (the second added by owner decision, 2026-11-08, after the review).** `.stignore` starts with `#include .stglobalignore` (only when that file exists) and then `!/.stglobalignore`; variants of both lines further down (other spacing, `./`, a leading byte order mark) are dropped, and every other line keeps its content and order. The second line keeps the shared file itself synced in a folder whose own lines are an allow list ending in `*` ("ALL Photos"): without it, `.stglobalignore` is ignored there, so it would neither arrive from a peer nor be sent. In a folder without `.stglobalignore`, `machine` adds `!/.stglobalignore` and removes an include line (an include of a missing file keeps the folder in an error state); Syncthing reports a peer's copy as `global` even while this device still ignores it (checked in the review), so the creation check runs in the same pass. After changing `.stignore`, `machine` asks Syncthing to rescan the folder (`POST /rest/db/scan`), so that the changed ignores apply at once. A byte order mark at the start of `.stignore` is removed, because Syncthing takes it as part of the first pattern and the include would silently not work.
8. **`.claude/worktrees` is ignored (owner decision, 2026-11-08, replacing the earlier decision to sync them).** The shared rule list gets `**/.claude/worktrees`, without `(?d)`, so that Syncthing never deletes a worktree on its own; uncommitted work in a worktree is then no longer synced.
9. **The Synology folders are shared rules (owner decision, 2026-11-08).** `(?d)@eaDir`, `(?d)#recycle` and `(?d)#snapshot` move into the repository rule list; the owner's convention `__*` stays a local line of each device.
10. **Trigger: a `machine` step (owner decision, 2026-11-08).** The step `syncthing ignores` runs in `machine setup`, `machine apply` and `machine update`, because the work is per user, needs no root, and the background update wires up newly accepted folders without a manual run.
11. **One rule list in the repository (owner decision, 2026-11-08).** `machine/syncthing/stglobalignore` holds the shared rules; it seeds the default ignore patterns and a newly created `.stglobalignore`.
12. **The live configuration comes from `syncthing paths` (owner decision, 2026-11-08).** On the L13 it prints `~/.config/syncthing/config.xml` while the database is under `~/.local/state/syncthing`; the first existing file of the two directories is only a fallback when the command fails.
13. **Only the login user's own Syncthing instance (owner decision, 2026-11-08).** Folders outside the home directory are included; folders the user cannot write are reported and skipped.
14. **The include line only for an existing `.stglobalignore` (owner decision, 2026-11-08).** A missing include target puts the folder into an error state, so the include line is added only after the file exists (decision 4).
15. **Syncthing becomes optional on servers, off by default (owner decision, 2026-11-08).** It stays preselected on private desktops and excluded for work and in containers.
17. **Conflict copies of `.stglobalignore`: deleted when identical, otherwise reported (owner decision, 2026-11-08).** A conflict copy (`.sync-conflict-<date>-<time>-<device>` in its name) whose content equals the current `.stglobalignore` is deleted; one with other content is reported and kept, because Syncthing keeps the newer file and renames the older one, so the copy can hold rules or exceptions of another device. Task 1.2 showed that identical content gives no conflict copy, so the deletion is a safety net.
16. **The name stays `.stglobalignore` (owner decision, 2026-11-08).** "Default ignore" would be confused with Syncthing's own default ignore patterns, and renaming would mean editing `.stignore` by hand on every device of "ALL Documents", the NAS and the phone included.

## Implementation outline

- **Module** `machine_cli/syncthing_ignores.py` with small functions that tests can call directly:
  - `find_config(home) -> Path | None`: the configuration file printed by `syncthing paths`; when the command fails, the first existing `config.xml` of `~/.local/state/syncthing` and `~/.config/syncthing`.
  - `folders(config) -> list[(folder_id, path)]`: the `<folder id=... path=...>` entries, `~` expanded.
  - `wired(lines, has_shared) -> lines`: the `.stignore` lines with `#include .stglobalignore` (when the shared file exists) and `!/.stglobalignore` on top, variants of both dropped, other lines unchanged (decision 7).
  - `global_state(api, folder_id)`: `GET /rest/db/file?folder=<id>&file=.stglobalignore`; `unknown` for 404, `present` or `deleted` for a `global` entry, `no answer` otherwise. A file deleted on another device is not recreated.
  - `ensure_folder(api, folder_id, path, rules) -> status`: when `.stglobalignore` is missing, makes sure `.stignore` has `!/.stglobalignore` and no include line; then, for a folder that is not paused and whose `global_state` is `unknown`, creates it from `rules`; `deleted` is left alone quietly; otherwise (present, folder paused, key rejected, no answer) returns `waiting`; when it exists, makes sure `.stignore` (missing counts as empty) starts with the two lines and writes it only when `wired` changed it. Never overwrites an existing `.stglobalignore`. Returns `ok`, `created`, `changed`, `waiting` or `skipped: <reason>`.
  - `clean_conflicts(path) -> list[status]`: finds conflict copies of `.stglobalignore` in the folder root (Syncthing names them `.sync-conflict-<date>-<time>-<device>.stglobalignore`), deletes the ones with the same content as `.stglobalignore` and reports the others (decision 17).
  - `ensure_defaults(api, rules)`: reads the current default ignore patterns and writes the rules followed by the existing lines that are not among them (`GET`/`PUT /rest/config/defaults/ignores`); writes nothing when the result equals the current list. Without a running Syncthing, it is left for the next run.
  - The REST address and API key come from `config.xml` (`<gui><address>`, `<apikey>`, `tls`); requests bypass any proxy, so the key never leaves the host. A unix socket or an address without a host is not used. Folders come from `<folder>` (the paused flag is the child element `<paused>`); a path that is not absolute after expanding `~` is skipped.
  - The step stays silent when Syncthing is not running and every folder is in place; a rejected API key (401, 403) is reported. One folder that fails (an unreadable `.stignore`, a read-only folder) is reported and the other folders and the defaults are still handled.
- **Shared rule list** `machine/syncthing/stglobalignore`: a comment header like the one on the NAS, then `(?d)@eaDir`, `(?d)#recycle`, `(?d)#snapshot`, the build and cache rules of the initial content above, and `**/.claude/worktrees`.
- **Step**: a mixin method `run_syncthing_ignores` on `Machine`, run as its own step `syncthing ignores` after `dotfile apply` in `machine setup`/`machine apply` (`machine_cli/commands.py`) and in `_update_steps` (`machine_cli/updates.py`), only when `syncthing` is in the host's features after `features.split(...)`. It logs one line per created, changed, waiting or skipped folder and nothing when everything is already in place. A failure warns and does not fail other steps.
- **Feature table**: `syncthing` gets `server: optional`, and its help becomes, for example, "Syncthing package + shared ignore rules".
- **Docs**: a Syncthing paragraph in `docs/features.md` (scheme, exceptions, the rules to add by hand to an existing `.stglobalignore`, manual setup for hosts without the dotfiles); the new module in the table of `docs/architecture.md`.

## Testing

Unit tests in `tests/unit/test_syncthing_ignores.py`, with a temporary `HOME` and a hand-written `config.xml` (the pattern of `tests/unit/test_mise_tools.py`; `system.run` and `system.have` replaced where Syncthing would be called):

- `config.xml` comes from `syncthing paths`, and from `~/.local/state/syncthing` or `~/.config/syncthing` when the command fails; without any, the step does nothing and prints nothing.
- A folder without `.stglobalignore` that no device knows gets the file from the rule list and then the include line; one that a peer has (global entry present), that is paused, or that cannot be checked (Syncthing not running) is reported as waiting and gets no include line.
- A folder without `.stignore` but with `.stglobalignore` gets a `.stignore` with the include line and `!/.stglobalignore` only.
- An allow-list folder (`(?d)*`) without `.stglobalignore` gets `!/.stglobalignore`, the shared file and the include line in one run, followed by a rescan request; an include without the shared file is removed; a byte order mark is removed also when both lines are already in place; a file deleted on a peer is left alone without a message; include variants (spacing, `./`, a byte order mark) further down are replaced by one include line.
- `<paused>true</paused>` is read; relative folder paths are skipped; a rejected API key is reported; the step prints nothing when Syncthing is not running and all is in place; one broken folder does not stop the others.
- A `.stignore` with local lines gets the include line on top; the local lines keep content and order.
- An include line further down is moved to the top and not duplicated.
- A second run changes no file (content and mtime unchanged).
- An existing `.stglobalignore` keeps content and mtime.
- A conflict copy with the same content as `.stglobalignore` is deleted; one with other content is kept and reported.
- A folder whose path is missing or not writable is reported and skipped; the other folders are still handled.
- The default ignore patterns are the repository rule list followed by the existing lines that are not in it (`__*` kept, the Synology lines not duplicated); a second run writes nothing.
- Without the feature `syncthing`, nothing is read or written.
- The step runs in `setup`, `apply` and `update` and a failure in it does not fail the other steps (in the existing step tests of `tests/unit/test_machine_cli.py` or `tests/unit/test_update_and_env.py`).

## Risks / Trade-offs

- [Two devices create `.stglobalignore` at the same time before they have seen each other] → Both write the same content from the repository, and identical content gives no conflict copy (task 1.2).
- [A device creates `.stglobalignore` while the peers that have a different one are not connected, for example a newly accepted folder while the NAS is offline] → The 404 only covers peers whose index has arrived (task 1.2), so a device whose index never arrived is not seen. Then the files differ, Syncthing keeps the newer one (the repository version) and a `.sync-conflict` copy of the other, and `machine` reports that copy (decision 17); the owner restores the right version by hand.
- [A peer announced `.stglobalignore` but never delivers it] → The folder stays reported as waiting on each run, without an include line and without an error.
- [`#include` of a file that does not exist yet puts the folder into an error state] → Verified with Syncthing v2.1.5 (see Verified with Syncthing v2.1.5). The include line is therefore added only when `.stglobalignore` exists.
- [Syncthing rewrites `config.xml` while it runs and may drop a direct edit] → Use `PUT /rest/config/defaults/ignores` of the running instance (verified in task 1.1).
- [The rule list in the repository and a folder's `.stglobalignore` drift apart] → The repository copy only seeds new folders; the synced file wins for existing ones, because its rules come first.
- [`(?d)` lets Syncthing delete ignored build output when it blocks a directory deletion] → Build output is rebuilt locally, so losing it costs a rebuild only.

## Migration Plan

On the first `machine apply` or `machine update` after the change, each host with the feature gets the include line in every folder's `.stignore` whose `.stglobalignore` exists or could be created, and the default ignore patterns. On the L13, "ALL Photos" and "Photo Sync Ditschi" get a new `.stglobalignore` when no other device has one. The existing `.stglobalignore` of "ALL Documents" is not changed by the dotfiles; the owner adds the Synology rules and `**/.claude/worktrees` there by hand (on the NAS or any device), as described in `docs/features.md`. Rollback: revert the change; the include lines stay and are harmless, and the owner removes them by hand if wanted. Hosts without the dotfiles are set up by hand once, as described in `docs/features.md`.

## Verified with Syncthing v2.1.5 (task 1.1, 2026-11-07)

Checked on ThinkPad-L13-Yoga-Gen-2 with the installed Syncthing v2.1.5. The tests ran in a separate throwaway instance (own home directory under the session scratchpad, GUI on 127.0.0.1:18384, listening only on localhost, no discovery and no relays). The live instance was only read, not changed.

- **Live instance on the L13:** Syncthing runs as the login user `ditschi`, started from the GNOME session (scope `app-gnome-syncthing-restart.scope`); the packaged `syncthing.service` user unit is disabled. `syncthing paths` prints the configuration file `~/.config/syncthing/config.xml` and the database `~/.local/state/syncthing/index-v2`, so configuration and data are in different directories. The GUI and REST API listen on `127.0.0.1:8384` without TLS.
- **Folders on the L13:** "ALL Photos" (`/home/family/photo`), "ALL Documents" (`/home/family/documents`) and "Photo Sync Ditschi" (`/home/family/photo/_Photo_Sync_Ditschi`). All three paths are writable by `ditschi`; `/home/family` belongs to `ditschi`, group `family`. Only "ALL Documents" has a `.stglobalignore`, and its `.stignore` already starts with `#include .stglobalignore`. The `.stignore` of "ALL Photos" is an allow list: `!` lines followed by `(?d)*`.
- **Current `.stglobalignore` of "ALL Documents":** it differs from the initial content above by an opt-in exception `!/DIY/uCPU und Elektronik/ext_resources/**` above the rules (vendored micropython/btstack sources contain a source directory named `target`).
- **Current default ignore patterns on the L13:** `<defaults><ignores>` already holds four lines: `(?d)@eaDir`, `(?d)#recycle`, `(?d)#snapshot`, `__*`.
- **Missing include target:** a `.stignore` with `#include .stglobalignore` and no such file puts the folder into the state `error` ("loading ignores: parse error: failed to load include file .stglobalignore: file not found"); `/rest/db/ignores` returns an empty `expanded` list. Once the file exists, the next scan clears the error. Not tested: whether a folder in this state still receives files from a peer. A folder in an error state does not sync, so a new device could probably never receive the `.stglobalignore` that would clear the error.
- **Default ignore patterns while Syncthing runs:** `GET` and `PUT /rest/config/defaults/ignores` with body `{"lines": [...]}` (header `X-API-Key`; key and GUI address come from `config.xml`). `PUT` returned 200, and Syncthing wrote the lines to `<defaults><ignores>` in `config.xml` itself. The CLI offers the same as `syncthing cli config defaults ignores`.
- **Default ignores and new folders:** a folder added through `POST /rest/config/folders` did not get the default ignore patterns; no `.stignore` was written. The default patterns are applied by the web GUI when it adds or accepts a folder (from Syncthing's documentation, not tested here).
- **Reloading `.stignore`:** `GET /rest/db/ignores` read a changed `.stignore` without a rescan. `POST /rest/db/ignores?folder=<id>` with `{"ignore": [...]}` writes `.stignore` and makes the running instance load it at once.

### Peers and conflicts (task 1.2, 2026-11-08)

Checked with two throwaway Syncthing v2.1.5 instances that were connected only to each other on localhost (own home directories in the session scratchpad, no discovery, no relays) and shared one folder:

- **No device has the file:** `GET /rest/db/file?folder=<id>&file=.stglobalignore` answers `404 No such object in the index`.
- **A peer has the file:** after the peer scanned it, the answer is 200 with a `global` entry (`deleted: false`), on the peer and on the other device.
- **Folder paused on this device:** the answer is 404 even though the peer has the file, because a paused folder does not process the peers' indexes. A 404 therefore means "no device whose index this device has received has the file". It does not cover peers that were never connected, or a paused folder.
- **Created on both devices while they were not connected:** a file with identical content on both sides gave **no** conflict copy after they reconnected. A file with different content gave a `.sync-conflict-<date>-<time>-<device>` copy on both devices.

## Assumptions

- ditschi-ThinkPad-T480 has no host config in `machine/hosts/` today; it gets the behaviour only after `machine setup` on it selects the feature `syncthing`.
- On other hosts with the feature, Syncthing also runs as the login user that runs `machine`, as verified on the L13.

## Open Questions

None. The owner answered all of them on 2026-11-08 (decisions 4, 6 and 8-16).
