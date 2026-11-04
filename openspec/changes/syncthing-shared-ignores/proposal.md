# Proposal

## Why

On 2026-11-03 and 2026-11-04 the owner found that the Syncthing folder "ALL Documents" (folder id `sp5jz-xtqrx`, on the Synology NAS at `/volume1/documents`, on the laptop ThinkPad-L13-Yoga-Gen-2 at `/home/family/documents`, shared with 11 devices) had synced the build output and dependency directories of development projects under `DIY/sbx`: Rust `target/`, `node_modules/`, `.venv` and tool caches. The builds came from two laptops, ThinkPad-L13-Yoga-Gen-2 and ditschi-ThinkPad-T480. In one day 117,511 distinct files were synced, the Syncthing index database on the NAS grew to 82 GB, the NAS disks were close to 100 % busy, and Hyper Backup on the NAS ran 3 to 6 hours instead of about 1 hour.

The owner wants build output never to be synced in any share by default, and synced only where it is explicitly enabled. Rolling the rules out to all hosts does no harm.

Syncthing has no global ignore list for existing folders. A folder's `.stignore` is never synced, but it can `#include` a file inside the folder, and that included file is synced. The owner therefore chose one synced file `.stglobalignore` at the root of each shared folder that holds the shared rules, loaded by every device's local `.stignore`. The file already exists on the NAS for "ALL Documents" since 2026-11-04. On hosts with the dotfiles, the dotfiles should wire it up for every folder and make new folders start with the same rules.

## What Changes

- On hosts with the feature `syncthing`, `machine` makes sure that the local `.stignore` of every folder in the local Syncthing configuration starts with `#include .stglobalignore`, and leaves the device's other lines as they are.
- On the same hosts, `machine` sets the shared rules as Syncthing's default ignore patterns (`<defaults><ignores>`), so that a new folder gets them from the start.
- The dotfiles never write or overwrite `.stglobalignore`; its content is owned by the synced folder.
- The repository gets one copy of the shared rule list, used for the default ignore patterns.
- `docs/features.md` describes the scheme, how to add an opt-in exception, and the one-time manual setup for hosts without the dotfiles.
- Unchanged: the feature table values of `syncthing` (preselected on private desktops, excluded for work, on servers and in containers) and the `syncthing` apt package.

## Capabilities

### New Capabilities

- `syncthing-ignores`: shared Syncthing ignore rules per folder (`.stglobalignore`), the `#include` line in every local `.stignore`, and the default ignore patterns for new folders, on hosts with the feature `syncthing`.

### Modified Capabilities

None. `feature-selection` keeps its values for `syncthing`; only the help text in the feature table may change, which no requirement fixes.

## Impact

- Code: a new module `machine_cli/syncthing_ignores.py`, called as its own step from `machine setup`, `machine apply` and `machine update` (`machine_cli/commands.py`, `machine_cli/updates.py`), see design.md.
- Data: the shared rule list in the repository (location in design.md).
- Tests: `tests/unit/test_syncthing_ignores.py`; the step wiring in the existing step tests.
- Docs: `docs/features.md`, `docs/architecture.md` (module table).
- Profiles: private desktops with the feature `syncthing` (today ThinkPad-L13-Yoga-Gen-2; see the Assumptions in design.md for ditschi-ThinkPad-T480). Work hosts, servers and containers are not affected, because the feature is excluded there.
- Outside the dotfiles: the Synology NAS, the Android phone, the Raspberry Pi and the family laptops are set up by hand once.

## Where the change is made

These planning artifacts are written in the live checkout and pushed to main, because they touch only `openspec/`. The implementation edits `machine_cli/`, which the host's `machine` command runs directly from the live checkout, so it is made in the worktree `$(machine repo)/.worktrees/syncthing-shared-ignores` on branch `syncthing-shared-ignores`, created from a main that already holds this change directory.
