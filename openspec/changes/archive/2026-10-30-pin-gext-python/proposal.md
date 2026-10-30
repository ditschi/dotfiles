# Proposal

## Why

The uv lock for `gnome-extensions-cli` inherits the package's Python `>=3.8` range, so it pins vulnerable `urllib3`/`requests` versions for Python 3.8 and 3.9 that no host uses, and GitHub raises 11 Dependabot alerts for them. Our hosts only need Python 3.10 or newer, so the lock should cover only the Python we run.

## What Changes

- `pipx:gnome-extensions-cli` in `home/gnome/.config/mise/conf.d/60-gnome.toml` gets the tool option `python = "3.14"`. mise then writes `requires-python = "==3.14.*"` into the generated `pyproject.toml`, and the uv lock holds one resolution with `urllib3` 2.8.0 and `requests` 2.34.2.
- The lock (`home/core/.config/mise/mise.lock` and `home/core/.config/mise/locks/pipx-gnome-extensions-cli/…`) is regenerated with `mise lock --global --platform linux-x64,linux-arm64`.
- Every `pipx:` tool must set a Python minor; the existing repository check `machine_cli/mise_check.py` (pre-commit hook) reports a pipx tool without one, so a future pipx tool cannot bring the old multi-Python lock back.
- On `gnome` hosts mise downloads its own CPython 3.14 (about 30 MB) for this tool. `python3` on `PATH` stays the system Python.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `user-tools`: adds a requirement that tools installed through the pipx backend pin one Python minor, so their locked dependencies cover only that Python and the system `python3` stays first on `PATH`.

## Impact

- Profiles: hosts with the `gnome` feature (private and work desktops); the `gnome` group is not selected on servers, containers or the Raspberry Pi.
- Files: `home/gnome/.config/mise/conf.d/60-gnome.toml`, `home/core/.config/mise/mise.lock`, `home/core/.config/mise/locks/pipx-gnome-extensions-cli/`, `machine_cli/mise_check.py`, `tests/unit/test_mise_check.py`.
- Disk/network: one extra mise-managed CPython download on `gnome` hosts.
- Closes the 11 open Dependabot alerts on `main` once merged.
- Where: worktree `.worktrees/pin-gext-python` on branch `pin-gext-python`, because `home/` is live in the main clone and the mise config change would affect the host's tools immediately.
