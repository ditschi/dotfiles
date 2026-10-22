## 1. Default on work machines

- [x] 1.1 In `tests/integration/conftest.py` resolve `INSECURE_TLS`: explicit `0`/`1` wins, otherwise on when the `machine` CLI's `default_profile()` is `work-machine`, off if the CLI cannot be imported. Verify: unit-style check of the resolver for the four cases (explicit 0, explicit 1, work, other) in `tests/unit`.
- [x] 1.2 Update the Readme test section. Verify: the text names the automatic default and the override.
- [x] 1.3 Run `pre-commit run --all-files` and `pytest tests/unit -q` (venv python first on `PATH`).
