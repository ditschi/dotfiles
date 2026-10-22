# Proposal

## Why

On work machines the network intercepts TLS, so the Docker tests fail unless `DOTFILES_TEST_INSECURE_TLS=1` is set by hand each time. The owner wants the option to be used automatically on work machines.

## What Changes

- The Docker tests enable the insecure-TLS test option automatically when the host is a work machine (same detection as `machine`: saved or repo host profile `work-machine`, or the work user-name pattern).
- An explicit `DOTFILES_TEST_INSECURE_TLS=0` or `=1` overrides the detection.
- Never applies outside the test image and containers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tests-and-ci`: the insecure-TLS test option defaults to on for work machines and stays off elsewhere.

## Impact

- Affected profile: `work-machine` hosts running the Docker tests.
- Code: `tests/integration/conftest.py`; docs: Readme test section.
