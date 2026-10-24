# Tasks

## 1. Testenv module

- [x] 1.1 Add `machine_cli/testenv.py` (standard library only): generate the image from the host's `/etc/os-release` with the user's identity for rootless and rootful Docker, mount the home with `fuse-overlayfs` over a read-only bind, run the command through the login shell with `sys_admin` dropped. Verify `python3 machine_cli/testenv.py -- 'touch ~/dotfiles/PROBE'` leaves no file on the host, with rootless and rootful Docker (`DOCKER_CONTEXT`).
- [x] 1.2 Add `--profile` (default: host's saved profile via `MACHINE_PROFILE_OVERRIDE`) and `--rebuild`; discard the change layer on exit. Verify a second run does not see the changes of the first.
- [x] 1.3 Register `machine testenv` and pass all arguments, including `--help`, to the module. Verify `machine testenv --help` shows the testenv options.

## 2. Tests and docs

- [x] 2.1 Add `tests/unit/test_testenv.py` for argument parsing, the shell command, the `docker run` arguments (read-only home, volume, identity, profile) and the generated Dockerfile. Verify `pytest tests/unit/test_testenv.py -q` passes.
- [x] 2.2 Describe the testenv in the Readme "Tests" section (quoting, limits inside the container). Verify the examples run.
- [x] 2.3 Run `pre-commit run --all-files` and `pytest tests/unit -q`. Verify both pass.
- [x] 2.4 Run `openspec validate add-machine-testenv --strict`. Verify it passes.

## 3. Use

- [x] 3.1 Test what `machine update` does on a host still on the old layout: `machine testenv -- 'machine update; machine'`, then with the manual steps first (stash, switch branch). Verify the outcome matches the host and the host home is unchanged.
