## 1. Tests and docs

- [x] 1.1 Add a unit test in `tests/unit/test_zsh_handoff.py`: with the marker present, `run_bashrc` output contains the hint exactly once; without the marker it does not
- [x] 1.2 Remove the "Update hint in bash" entry from `openspec/backlog.md`
- [x] 1.3 Run `uvx nox -s tests -- -q -k handoff`, then archive the change
