# Tasks

## 1. Rename

- [x] 1.1 Rename `ansible/roles/thinkpad_l13_yoga_gen2/files/touchpad-reset` to `files/mouse-reset`; install it to `/usr/local/bin/mouse-reset` and remove `/usr/local/bin/touchpad-reset` in `tasks/main.yml`. Update the role README and `docs/thinkpad-l13-yoga-gen2.md`.

## 2. Checks

- [x] 2.1 Run `pre-commit run --files` on the changed paths and `ansible-lint ansible/*.yml`. No pytest run: no Python code, test or test configuration changes, and no unit test covers this role.
  Result (2026-10-30): all pre-commit hooks passed or were skipped; `ansible-lint` (via `uvx`) passed with 0 failures and 0 warnings in 40 files. `grep -rln 'thinkpad_l13\|touchpad-reset' tests` finds nothing.
- [ ] 2.2 On the owner's L13 Yoga Gen 2, after merging: run `machine apply`; `/usr/local/bin/touchpad-reset` is gone and `mouse-reset` reloads `elan_i2c`.
