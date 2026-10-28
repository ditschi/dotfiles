## 1. Owner Matching

- [x] 1.1 Add HTTPS and SCP-style SSH `*_bosch` owner rules.
- [x] 1.2 Cover matching owners and nonmatching repository names/owner substrings.
- [x] 1.3 Document the updated owner behavior.

## 2. Validation

- [x] 2.1 Run focused Git configuration tests (42 passed).
- [x] 2.2 Run `pytest tests/unit -q` (240 passed via `python3 -m pytest -c tests/pytest.ini tests/unit -q`).
- [x] 2.3 Run `pre-commit run --all-files`.
- [x] 2.4 Verify the active PLANS repository selects the work identity and credential username.
