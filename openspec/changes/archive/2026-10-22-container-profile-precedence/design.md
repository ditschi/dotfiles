# Design

## Context

The owner decided that in a container the container setup always applies (see `openspec/investigations/architecture-and-profiles.md`, B1, B2, B4). Current behaviour:

- `profile.py` `default_profile()` reads the saved profile first, then the host profile, then Docker detection, then `MACHINE_PROFILE`, then the company user ID format.
- `home/dot_zsh/machine-profile.sh` reads the saved profile and the user ID format only, with no Docker check.
- The integration tests run the other profiles inside Docker with `./bootstrap --profile <profile> --yes` (`tests/integration/conftest.py`, `profile_env`), so a plain "Docker means container" rule would break them.

## Goals / Non-Goals

**Goals:**
- One rule for CLI and shell: Docker means `container`.
- A way for the test images to run another profile.
- `WORK_SETUP` follows the profile in containers.

**Non-Goals:**
- Changing the profile choice outside Docker.
- Moving the company user ID pattern to local configuration (separate idea, see B5/B7 of the report).

## Decisions

1. **Docker check first.** In Docker the profile is `container` unless the override is set. The saved profile and host profile are not read for this decision, so a shared home no longer leaks the host profile into a container.
2. **Override variable `MACHINE_PROFILE_OVERRIDE`.** It applies only in Docker and is set at container level by the tests, so every exec in the container sees it. A saved profile cannot serve as override, because it is indistinguishable from a host's profile in a shared home.
3. **`WORK_SETUP` follows the effective profile.** In `container` it is unset. Outside containers the existing rule stays (profile `work-machine` or company user ID).
4. **Detect Docker the same way in both places.** The shell uses `/.dockerenv` or `MACHINE_IN_DOCKER=1`, like `system.in_docker()`.

## Risks

- A tool inside a company dev container that reads `WORK_SETUP` stops seeing it (open question in proposal.md).
- Anyone who relied on a saved non-container profile inside a container now needs the override.

## Investigations (not decided, not in the specs)

None added by this change. It implements the owner's decision from the earlier investigations.
