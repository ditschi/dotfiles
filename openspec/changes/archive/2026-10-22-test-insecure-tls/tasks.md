## 1. Implementation

- [x] 1.1 Add the `INSECURE_TLS` build arg to `tests/docker/Dockerfile` and the runtime env in `tests/integration/conftest.py`
- [x] 1.2 Document the flag in the Readme "Tests" section
- [x] 1.3 Run `DOTFILES_TEST_INSECURE_TLS=1 uvx nox -s docker` (14 passed)
