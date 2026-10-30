# Design

## Context

See proposal.md - Why. mise installs `pipx:` tools with uv when `lockfile = true`. For each such tool it writes a `pyproject.toml` and `uv.lock` under `~/.config/mise/locks/pipx-<tool>/<version>/` (linked into `home/core/.config/mise/locks/`). The generated `pyproject.toml` copies the package's own `requires-python`, so uv adds a separate resolution for each Python range the package supports. `gnome-extensions-cli` 0.11.0 declares `>=3.8, <4.0`, which yields pins for Python 3.8, 3.9 and 3.10+.

Today, without a Python option, the tool's venv uses the system Python (3.14.4 on the owner's host), so the installed tool already gets the patched `urllib3` 2.8.0. The vulnerable pins are only in the lock file, not on any host.

Spike with mise 2026.10.15 in an isolated scratch project (own `MISE_DATA_DIR`/`MISE_CACHE_DIR`):

| Option on the tool | Result |
|---|---|
| `uvx_args = "--python 3.12"` | rejected: "dependency locking does not support uvx_args or pipx_args" |
| `python = ">=3.10"` | rejected: only a CPython minor (`3.12`) or exact patch (`3.12.12`) is accepted |
| `requires_python = ">=3.10"`, or `python` as a separate tool | ignored; lock still covers `>=3.8` |
| `python = "3.12"` | `requires-python = "==3.12.*"`, one resolution: `urllib3` 2.8.0, `requests` 2.34.2; install works, `gext --help` runs |
| `python = "3.14"` | `requires-python = "==3.14.*"`; install works but mise downloads CPython 3.14.10 although the system has 3.14.4 |

In every case `python3` on `PATH` stayed `/usr/bin/python3`.

## Goals / Non-Goals

**Goals:**
- The committed lock contains no dependency pins for Python versions we do not run.
- A future pipx tool cannot reintroduce multi-Python locks unnoticed.

**Non-Goals:**
- Pinning the system Python or adding Python as a global mise tool.
- Changing how `machine` uses `gext` (install/enable of extensions stays as is).

## Decisions

- **Per-tool option `python = "3.14"`** on `pipx:gnome-extensions-cli`. It is the only option mise accepts for locked pipx installs that narrows `requires-python`. The minor 3.14 was chosen by the owner.
- **Repository check for every pipx tool** in `machine_cli/mise_check.py`, which pre-commit already runs on the group fragments (one declaration per tool, no Ansible duplicate). It reports a `pipx:` tool that is not a table with a `python` key, naming the tool and fragment; covered by `tests/unit/test_mise_check.py`.
- **Keep `version = "latest"`**; the version stays pinned by `mise.lock` as for every other tool.

Alternatives considered:
- **Dismiss the Dependabot alerts** and keep the system Python: rejected by the owner in favour of a lock that matches what we support; alerts would return with each new lock.
- **`uv tool install` from `machine`** (as for `azure-cli`): removes the lock and with it the alerts, but the tool version would no longer be pinned in `mise.lock`.
- **Wait for upstream** to drop Python 3.8/3.9: no control over timing.

## Risks / Trade-offs

- [mise downloads a separate CPython 3.14 (about 30 MB) on each `gnome` host, even when the system Python is 3.14] → accepted trade-off; it lives under `~/.local/share/mise/installs/python/` and is not on `PATH`.
- [The mise-managed Python must exist for `linux-arm64` too when the lock covers that platform] → `gnome` is not selected on arm64 hosts today; `mise lock` for both platforms must still succeed.
- [A newer mise may change the option name or behaviour] → the repository check and the lock diff make a change visible; spike was done on 2026.10.15.
- [After the change the existing venv on a host is rebuilt with the new Python at the next `machine update`] → no user action; `gext` is only used by `machine`.

## Migration Plan

Merge the branch; `machine update` on `gnome` hosts installs CPython 3.14 through mise and reinstalls `gnome-extensions-cli` from the new lock. Rollback: revert the commit and re-run `machine update`.
