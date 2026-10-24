# Proposal

## Why

Updates have broken the `machine` command on a host before, and that was only noticed after the update had already changed the real home. Larger changes, like the move to mise dotfile groups, need a safe way to run `machine update`, `machine setup` or a plain `machine` against the real state of a host first, without changing the real home. The same helper should be usable right away to test a pending update from a host that still runs the old layout.

## What Changes

- New command `machine testenv [OPTIONS] [-- COMMAND]`. It starts a container with the current home behind a copy-on-write overlay: the real home is read-only, all changes go into a throwaway layer. Without COMMAND it opens an interactive login shell; with COMMAND it runs it and returns its exit code, e.g. `machine testenv -- 'machine update && machine'`.
- Options: `--ref REF` checks out a commit-ish in `~/dotfiles` inside the container first (to test a branch or a pending update), `--diff` lists the files the command changed in home, `--keep NAME` keeps the layer in a named volume to re-enter or inspect later (`--reset` starts it again from the real home, `--list` shows kept ones), `--profile` sets the machine profile inside (default: the host's saved profile), `--rebuild` rebuilds the image.
- The implementation (`machine_cli/testenv.py`) uses only the Python standard library, so it also runs directly from a checkout (`python3 machine_cli/testenv.py ...`) on a host whose installed `machine` is old or broken.

## Capabilities

### New Capabilities
- `home-testenv`: running commands against the real home in a container without changing it; isolation guarantees, profile selection, kept environments and the change listing.

### Modified Capabilities
- None. `tests-and-ci` lists repository tests; the testenv is a manual check of a host's own state and is described in the Readme "Tests" section.

Affected profiles: every profile on a host with Docker (rootless or rootful). Inside, the host's profile is used, so the run matches what an update would do on that host. Work machines need no root; rootless Docker is enough.

## Impact

- Code: new `machine_cli/testenv.py`, the `testenv` command in `machine_cli/machine`, `tests/unit/test_testenv.py`, Readme "Tests".
- Runtime: needs Docker and `/dev/fuse` on the host; builds a local image `machine-testenv:<distro>-<version>-<hash>` from the host's distribution. Kept environments are Docker volumes `machine-testenv-<name>`.
- No change to the update flow or to existing commands.
