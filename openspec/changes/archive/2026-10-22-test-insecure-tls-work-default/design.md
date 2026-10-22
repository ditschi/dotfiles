## Context

See proposal.md. `tests/integration/conftest.py` reads `DOTFILES_TEST_INSECURE_TLS` once and passes it to the image build and the containers.

## Decisions

- Detection reuses the `machine` CLI's own default-profile logic instead of a second copy, so "work machine" means the same thing everywhere. If the CLI cannot be imported (missing dependency) the test run treats the host as not a work machine and keeps TLS verification on.
- An explicit value of the variable wins over detection, so a work machine on a non-intercepting network can set `0`.
- Verification stays on by default everywhere else, including CI.
