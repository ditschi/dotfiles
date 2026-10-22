## Why

On hosts that intercept TLS, the Docker test image cannot be built (`ansible-galaxy` fails with `CERTIFICATE_VERIFY_FAILED`). The test containers are thrown away, so skipping verification there is acceptable.

## What Changes

- Docker tests accept the opt-in `DOTFILES_TEST_INSECURE_TLS=1`, which skips TLS verification in the test image and containers only. Off by default.

## Capabilities

### Modified Capabilities
- `tests-and-ci`: "Local test commands" gains the opt-in flag.

## Impact

Already implemented in commit `e2f8617` (`tests/docker/Dockerfile`, `tests/integration/conftest.py`, Readme).
