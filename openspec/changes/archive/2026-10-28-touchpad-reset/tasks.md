# Tasks

## 1. Command

- [x] 1.1 Add `files/touchpad-reset` to `ansible/roles/thinkpad_l13_yoga_gen2` (re-exec with sudo, `modprobe -r elan_i2c`, `modprobe elan_i2c`) and a task that installs it to `/usr/local/bin/touchpad-reset` with mode `0755`. Update the role README.
- [x] 1.2 Describe symptom, cause and fix in `docs/thinkpad-l13-yoga-gen2.md`.

## 2. Checks

- [x] 2.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `ansible-lint ansible/*.yml`. All three must pass.
- [x] 2.2 On the owner's L13 Yoga Gen 2: run `machine apply`, then `touchpad-reset`; touchpad and TrackPoint work afterwards and the `elan_i2c` count in `/proc/interrupts` grows while touching.
  Result (2026-10-28): `machine apply` installed `/usr/local/bin/touchpad-reset`; `touchpad-reset` printed "elan_i2c reloaded", the kernel registered Elan Touchpad and TrackPoint again at 23:28:25, and the `elan_i2c` interrupt count grew from 446693 to 467628.
