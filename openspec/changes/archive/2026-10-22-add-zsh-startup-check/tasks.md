# Tasks

Owner decisions applied (see design.md): no TTL fallback; reset is the `zsh-recheck` shell function; healthy means the config fully loaded, not just that zsh started.

## 1. Helper script

- [x] 1.1 Add `home/dot_zsh/zsh-handoff-check.sh` (bash-compatible) with: zsh executable check, `~/.zshrc` and `00_LOADER.zsh` readable check, trial login interactive zsh start with stderr capture, skip when the zinit directory is missing (no outcome cached), and treat a timeout as inconclusive (design decisions 7 and 8), and a "config fully loaded" probe (e.g. `00_LOADER.zsh` sets a marker variable at its end that the trial prints). Verify: unit test covers each failure reason including a partially loaded config.
- [x] 1.2 Implement state file under `${XDG_STATE_HOME:-~/.local/state}/dotfiles/zsh-handoff` with fingerprint-based validity (`-nt` comparisons, zsh path/version, `~/.dotfiles-update-available`). Verify: unit tests for cache hit (no trial start), and re-check after touching each watched file.
- [x] 1.3 Add `zsh-recheck` function that clears the state file. Verify: unit test.

## 2. bashrc integration

- [x] 2.1 Source the helper in the `home/dot_bashrc` handoff block before both `exec` paths (preferred-shell and default); on failure stay in bash and print the one-line diagnostic. Verify: unit test that existing guards (nested, non-interactive, command string, Docker) are unchanged.
- [x] 2.2 Ensure a missing helper file never breaks `.bashrc` (guard with `[ -r ... ]`). Verify: test with helper removed.

## 3. Tests and docs

- [x] 3.1 Add `tests/unit/test_zsh_handoff.py` using a fake `$HOME` and stub zsh binaries (missing, failing, noisy, healthy; fresh host without zinit; hanging). Verify: `pytest tests/unit -q` passes.
- [x] 3.2 (temporary, drop once `docs/decisions/` is retired) Update `docs/decisions/0002-shell-setup.md` (What, Last verified, Why bullets in the tagged docs notation) and note the new test in INV-0002. Verify: file reflects the change.
- [x] 3.3 Mention `zsh-recheck` in `Readme.md` if the Readme documents shell startup. Verify: grep shows entry.

## 4. Validation

- [x] 4.1 Run `pre-commit run --all-files` and `pytest tests/unit -q`; all pass.
- [x] 4.2 Manually verify on this host: healthy start, rename `00_LOADER.zsh` (stays in bash with diagnostic), restore and edit file (re-check passes).
