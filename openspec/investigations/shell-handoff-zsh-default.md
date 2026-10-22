# Investigation: zsh as the preferred interactive shell

Related specs: `shell-handoff`. Status: the owner decided that zsh stays preferred when installed unless another shell is explicitly configured; the findings below are kept as evidence.

- Question: Should zsh remain preferred on machines where `chsh` is unavailable?

## Evidence

- `.bashrc` exits immediately for non-interactive shells. The zsh handoff only runs for an interactive, top-level Bash session; it skips manually started or nested shells.
- The handoff respects `~/.preferred-shell` when that executable is available; this explicit override is checked before the Docker and command-string guards on the default fallback. Without the override, the fallback defaults to zsh where available, except in Docker, and skips Bash command strings. Non-interactive Bash exits before either path.
- `01_work.zsh` contains a Bosch-specific `chsh-bosch` helper describing an SSSD `override_shell = /bin/zsh` route. This indicates that changing the account shell may require a managed-system path rather than ordinary `chsh`; the linked internal instructions are not independently verifiable here.
- A workspace search found no tests that directly exercise the `.bashrc` shell handoff. Existing tests cover Bash and zsh for other CLI/update behavior, not this startup decision. Since the OpenSpec change `add-zsh-startup-check`, `tests/unit/test_zsh_handoff.py` covers the health check and the `.bashrc` integration.

## Recommendation

Keep zsh as the preferred interactive shell when the account's login shell cannot be changed. The guarded default Bash handoff gives a consistent setup without replacing explicitly nested shells or non-interactive commands. Where company policy supports changing the account shell, prefer that documented route; retain `~/.preferred-shell` as the explicit per-user override, including where it intentionally supersedes the default Docker fallback. Consider adding a focused startup test separately, since the current behavior is not directly covered.

This is a recommendation, not an owner-confirmed decision.
