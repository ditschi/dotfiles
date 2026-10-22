# Proposal

## Why

Inside a Docker container the container setup should always apply (owner decision). Today it does not:

- A saved profile wins over Docker detection, so a container that shares a host's home directory gets the host's profile and its full set of dotfiles.
- The shell (`machine-profile.sh`) never checks for Docker, so the CLI and the shell can disagree about the profile of the same container.
- A company user ID in a container sets `WORK_SETUP=true`, although the work modules are not linked in the `container` profile.

## What Changes

- In Docker (`/.dockerenv` or `MACHINE_IN_DOCKER=1`) the profile is always `container`, in the `machine` CLI and in the shell, before any saved profile is read.
- An explicit override variable `MACHINE_PROFILE_OVERRIDE` selects another profile in Docker. The Docker test images use it, because they test the other profiles inside containers.
- `WORK_SETUP` is no longer set in the `container` profile, also not for a company user ID.
- The company user ID check moves to one shared place instead of two copies (`profile.py` and `machine-profile.sh`).
- The test that expects `container|true` expects `container|` (empty) afterwards.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-profiles`: Docker detection comes first; the shell follows the same order as the CLI.
- `work-private-separation`: `WORK_SETUP` is not set in containers.

## Open Questions

- Do the project dev containers (`sdx`, company user ID) or other tools read `WORK_SETUP` inside the container? Unknown from this repository; if so, they lose it.
- Is the name `MACHINE_PROFILE_OVERRIDE` acceptable? It is a proposal, not confirmed.

## Impact

- Code: `home/dot_local/lib/machine_cli/profile.py`, `home/dot_zsh/machine-profile.sh`, `tests/integration/conftest.py` (pass the override into test containers), `tests/integration/test_profile_containers.py`, unit tests for both detection paths.
- Docs: `Readme.md` if it describes profile detection.
- Reports: `openspec/investigations/architecture-and-profiles.md` items B1, B2, B4.
