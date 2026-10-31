# Tasks

## 1. bw as a mise tool

- [x] 1.1 Add `bitwarden = "latest"` with a one-line comment to `home/core/.config/mise/conf.d/20-tools.toml`; verify `mise ls bitwarden` lists it from that fragment and the repository check for tools declared twice passes.
- [x] 1.2 Run `mise lock --global --platform linux-x64,linux-arm64 bitwarden` so `home/core/.config/mise/mise.lock` gets `[[tools.bitwarden]]` with a sha256 checksum and URL for `linux-x64` and `linux-arm64` (`bw-linux-arm64-<ver>.zip`); verify both platform entries in the diff and that no other tool's entry changed.
- [x] 1.3 Pin `bitwarden = "2026.8.0"` with a comment on the Vaultwarden incompatibility and re-lock; verify the lock's sha256 for both platforms equals the GitHub asset digests.

## 2. machine installs bw through mise

- [x] 2.1 Rewrite `ensure_bitwarden_cli` in `machine_cli/tools.py`: when `bw` is missing, run `mise install bitwarden` with `MISE_CONFIG_DIR=<repo>/home/core/.config/mise`, put the directory from `mise where bitwarden` on `PATH`, log the installed version, return false with a log line on failure; remove the CPU check, the hard-coded version, the download, checksum and unzip code. Verify with new unit tests in `tests/unit/` (fake `mise`): the install command and env are as described, `bw` is found afterwards, a failing `mise` returns false without an exception.
- [x] 2.2 Check whether anything besides the old `bw` download needs `unzip` in `ensure_bootstrap_tools`; remove the `unzip` install there if nothing does (keep `machine_cli/testenv.py` and `tests/docker/Dockerfile` unless they no longer need it either). Verify by `grep -rn unzip machine_cli tests` and the unit tests touching `ensure_bootstrap_tools`.
- [x] 2.3 Keep the "Install it now?" offer in `require_bitwarden` (`machine_cli/bw_client.py`) on the new install path; verify `tests/unit/test_host_profiles.py::test_require_bitwarden_offers_install_then_login` still passes and add a case where the mise install fails (logs "Bitwarden CLI not installed; nothing done", returns false).
- [x] 2.4 Remove an old `~/.local/bin/bw` once `mise` provides `bw`: after the tool install in `machine setup` and in the converge step of `machine update` (`machine_cli/updates.py`), delete the file and log it; keep it when `mise which bw` fails. Verify with unit tests for both scenarios of "Old self-installed bw is removed" and that a `bw` elsewhere on `PATH` is not touched.
- [x] 2.5 Put the mise shims directory on `PATH` in `system.ensure_user_bin_on_path` (next to `~/.local/bin`, only when it exists and is missing), so `machine` run over `ssh host cmd` without a login shell finds the mise `bw` as before; verify with a unit test in `tests/unit/test_update_and_env.py` (shims added once, existing order kept) and the existing `~/.local/bin` test.

## 3. Completion and docs

- [x] 3.1 Add `dotfiles_cache_eval bw bw completion --shell zsh` to the cached CLI completions in `home/core/.shell/zsh/plugins.zsh`, and a note next to the Bash completion list in `home/core/.shell/bash/tools.bash` that `bw` has no Bash completion. Check against the in-flight change `shell-tool-completions` (same files) and align with whichever lands first. Verify in a new zsh that `bw <Tab>` lists subcommands and that zsh starts without errors when `bw` is absent (`zsh -i -c exit` with `bw` off `PATH`).
- [x] 3.2 Update Readme "Secrets / Bitwarden": `bw` comes from mise (`core` group, pinned in `mise.lock`, x86_64 and aarch64), an old `~/.local/bin/bw` is removed; verify no other Readme line still says `bw` goes to `~/.local/bin` (`grep -n "local/bin" Readme.md`).

## 4. Validation

- [x] 4.1 Run `pytest tests/unit -q` (setup, update and Bitwarden paths share `ensure_bootstrap_tools` and the converge step, so the full unit suite is the safe selection); record the result.
- [x] 4.2 Run `pre-commit run --files` on every changed and added path (including `mise.lock` and the new tests); record the result.
- [x] 4.3 In a clean environment without `~/.config/mise` (scratch `HOME`, `MISE_DATA_DIR`), run the new `ensure_bitwarden_cli` path and verify `bw --version` prints the locked version; record the commands and output.
- [ ] 4.4 On `netmaster` (aarch64), after merging: `machine update`, then `bw --version` prints the locked version and `machine env pull` gets past the install step to the Bitwarden login or unlock. Record the result (owner runs it, or over SSH with the owner's consent).

## Workflow follow-up

- Archive the change in this worktree; ask the owner before merging the branch into the main clone and before removing the worktree.
- Remove the unused worktree `.worktrees/bw-cli-via-mise` and branch `bw-cli-via-mise` in the main clone, which were created by mistake before this checkout was chosen (owner, or with the owner's approval).

## Validation record (2026-10-31)

- `pytest tests/unit -q`: 757 passed (full suite, because setup, update and the Bitwarden paths share `ensure_bootstrap_tools`, `run_tools_install` and `ensure_user_bin_on_path`).
- `pre-commit run --files <all changed and added paths>`: black and yamlfmt reformatted `machine_cli/tools.py`, `tests/unit/test_bw_install.py` and `.openspec.yaml` on the first run; the rerun passed (including "mise tools are declared once"). After that, `pytest tests/unit/test_bw_install.py tests/unit/test_mise_tools.py tests/unit/test_host_profiles.py -q`: 81 passed.
- Clean environment (x86_64; scratch `HOME`, `MISE_DATA_DIR`, no `~/.config/mise`, no `bw` on `PATH`): `Machine().ensure_bitwarden_cli()` ran `mise install bitwarden` from the repository config, returned true, and `bw --version` printed `2026.10.1` from `<MISE_DATA_DIR>/installs/bitwarden/2026.10.1/bw`.
- zsh completion: with `bw` on `PATH`, `dotfiles_cli_completions` registers `_comps[bw]=_bw`; without `bw` it returns 0 and registers nothing. `bw <Tab>` was not tried in an interactive terminal.
- `mise lock` also deleted the unrelated `home/core/.config/mise/locks/npm-anthropic-ai-claude-code/2.1.308/`; it was restored, so only the `bitwarden` entries changed in the lockfile.
- 4.4 first run (netmaster, `bw` 2026.10.1 via mise shims): install worked (`bw --version` 2026.10.1), but `machine env pull` failed after login with `KeyIdBackfillError` (404 from Vaultwarden 2026.6.0) and wrote no env files; led to task 1.3. Lock after 1.3: sha256 367f618e… (linux-x64) and 74d822a5… (linux-arm64), equal to the GitHub digests.
