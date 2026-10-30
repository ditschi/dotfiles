# Tasks

Work only in the worktree `.worktrees/pin-gext-python` (branch `pin-gext-python`).

## 1. Repository check for pipx tools

- [x] 1.1 Extend `machine_cli/mise_check.py` so it reports every `pipx:` tool in a group fragment that is not a table with a `python` key, naming the tool and the fragment; add tests in `tests/unit/test_mise_check.py` for a pipx tool without `python` (fails, names tool and fragment) and with `python = "3.14"` (passes). Verify with `pytest tests/unit/test_mise_check.py -q` - the new failing-case test fails before 2.1 for the real repository (`test_repository_fragments_pass`) and passes after it.

## 2. Pin the Python minor and re-lock

- [x] 2.1 In `home/gnome/.config/mise/conf.d/60-gnome.toml` change the entry to `"pipx:gnome-extensions-cli" = { version = "latest", python = "3.14" }`, keeping the comment. Verify `python3 -m machine_cli.mise_check` reports nothing.
- [x] 2.2 Regenerate the lock from the worktree without touching the host's live mise setup (isolated `MISE_DATA_DIR`/`MISE_CACHE_DIR`/`MISE_STATE_DIR` and the worktree's `home/core/.config/mise` as config dir), equivalent to `mise lock --global --platform linux-x64,linux-arm64`. Verify: the generated `pyproject.toml` has `requires-python = "==3.14.*"`, `uv.lock` has exactly one `urllib3` (2.8.0) and one `requests` (2.34.2) entry and no `resolution-markers` for older Python, the `mise.lock` digest for the tool changed, and no other tool's entry in `mise.lock` changed (`git diff --stat`).
- [x] 2.3 In the same isolated environment run `mise install` for the `gnome` fragment and `gext --help`; verify the tool runs, its venv uses a mise-managed CPython 3.14, and `python3` on `PATH` is still `/usr/bin/python3`.
- [x] 2.4 Update the Readme mise section near the `mise lock` note with one sentence that `pipx:` tools must set `python = "<minor>"` and why. Verify the sentence is next to the existing lock instructions.

## 3. Validation

- [x] 3.1 Run `pytest tests/unit/test_mise_check.py tests/unit/test_mise_tools.py tests/unit/test_features.py -q` (repository check, mise tool install path incl. the `gnome` step, group/fragment selection) and record the result in this file.
- [x] 3.2 Run `pre-commit run --files` on all changed and added paths (including the change directory and the regenerated lock files) and record the result.
- [x] 3.3 Run `openspec validate pin-gext-python --strict` and record the result.

## Validation record

- `pytest tests/unit/test_mise_check.py tests/unit/test_mise_tools.py tests/unit/test_features.py -q`: 40 passed. Covers the new pipx check (both cases plus the real repository), the mise install path with the `gnome` extension step, and group/fragment selection.
- `pytest tests/unit/test_update_and_env.py -q`: 95 passed; the only other unit tests that read `mise.lock` (update classification of lock changes).
- `pre-commit run --files <all changed and added paths>`: exit 0 (yamlfmt added `---` to `.openspec.yaml` on the first run).
- `openspec validate pin-gext-python --strict`: valid.
- Lock regenerated with mise 2026.10.15 in an isolated `HOME`/`MISE_*` setup whose `mise.lock` and `locks/` link into this worktree; the main clone stayed clean. mise kept the old `0.11.0` entry beside the new `0.11.0~2ec0793d` one (no prune option), so the stale `[[tools."pipx:gnome-extensions-cli"]]` block and `locks/pipx-gnome-extensions-cli/0.11.0/` were removed; a second `mise lock` left `mise.lock` byte-identical. The lock now also pins `python` 3.14.10 for linux-x64 and linux-arm64.
- Isolated `mise install uv pipx:gnome-extensions-cli`: `gext 0.11.0` runs, venv on mise CPython 3.14.10 with `urllib3` 2.8.0; with the full global `mise env`, `python3` is `/usr/bin/python3`.

## Workflow follow-up

- Archive the change inside the worktree, then ask the owner before merging `pin-gext-python` into `main` and before removing the worktree.
- After merge and push, check that the 11 Dependabot alerts close on GitHub.
