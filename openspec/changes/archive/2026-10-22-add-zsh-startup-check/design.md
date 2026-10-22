# Design

## Context

`home/dot_bashrc` runs the handoff inline: guards on parent shell/`SHLVL`, then `~/.preferred-shell`, then default zsh unless Docker or a command string. It runs `exec zsh -l` without any check, so a broken zsh setup leaves no diagnosis. The loader is `~/.zsh/config/00_LOADER.zsh`. `07_machine.zsh` already caches under `${XDG_CACHE_HOME:-$HOME/.cache}/zsh/`. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Cheap cache hit (only `stat`-style tests in bash, no subprocesses).
- Bash-compatible, no root, works on all profiles.

**Non-Goals:**
- Changing which sessions hand off, or changing the account login shell (`chsh`).
- Auto-repairing zsh or installing it.
- Checking zsh plugin/network health (zinit clones etc.).

## Decisions

1. **Helper script, not inline.** Put the logic in a small bash-compatible file `~/.zsh/zsh-handoff-check.sh` (next to `machine-profile.sh`, which is already shared by both shells), sourced from the `.bashrc` handoff block. Keeps `.bashrc` readable and makes it unit-testable. Alternative: inline in `.bashrc` — rejected as untestable and noisy.
2. **Cache location:** `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/zsh-handoff` (state, not cache, because a cached failure changes behaviour). Plain `key=value` file: `status`, `reason`, `fingerprint`.
3. **Fingerprint-based invalidation** instead of TTL: the fingerprint is the zsh path plus its mtime and size, plus mtime of `~/.zshrc`, `~/.zsh/config/*.zsh`, `machine-profile.sh`, `~/.preferred-shell` and `~/.dotfiles-update-available` presence. Computed with `[ file -nt statefile ]` comparisons for the cheap path, so no hashing on a hit. No TTL fallback (see Confirmed decisions).
   Alternatives: always re-check — rejected (no repeated checks wanted); TTL only — rejected (stale after edits).
4. **Trial start:** the check starts zsh once as a login interactive shell with output captured, and treats a non-zero exit, error output or an incomplete config load as a failure. A generous timeout acts only as a hang guard; see decisions 7 and 8.
5. **Failure UX:** on failure stay in bash, print one line naming the failing check plus the hint to run `zsh-recheck`, a shell function defined in the helper (not a `machine` subcommand, since `machine` may be unavailable when zsh or pyenv is broken).
6. **Dotfiles-updated trigger:** the cache is invalidated when `~/.dotfiles-update-available` is cleared by `machine update`. Whether a repo revision comparison is also worthwhile is checked during implementation.
7. **Fresh hosts are not judged.** If the zinit installation directory is missing, the first zsh start is the setup run: the check is skipped, the session goes to zsh and nothing is cached, so the user sees the plugins install. Judging starts once zinit exists. Rejected: running the trial on a fresh host, because it would cache the slow, noisy install as a failure.
8. **Timeout is a hang guard and inconclusive.** The trial start has a generous timeout only so a hang (for example on network access) cannot freeze the shell. A timeout is not cached as a failure: the session stays in bash for that start and the next start re-checks. This avoids false failures after a new plugin makes one start slower. Rejected: no timeout, because a hung shell that never opens is the worst outcome; rejected: a short fixed timeout or install time as minimum, because both vary with the network and give false failures.

## Risks / Trade-offs

- Trial zsh start with p10k instant prompt or zinit may print benign stderr → false failure. Accepted by the owner: first version without an allow-list, reviewed on real hosts before finalising.
- Trial start costs about one zsh startup once per invalidation → acceptable, only on change. On a fresh host or after a new zinit plugin, that start can legitimately be slow or noisy (see Open Questions).
- Stale pass after an external change not in the fingerprint (e.g. zinit plugin update) → user can run the reset function.
- Cached failure keeps a user in bash after they fix the cause outside the fingerprint → same reset path; the diagnostic always prints it.

## Findings from the real-host check

- An interactive trial zsh without a terminal prints benign errors (zle, monitor, gitstatus). The trial therefore keeps the terminal on stdin when there is one, and runs under `timeout --foreground` so terminal access does not stop it.
- Removing or renaming a config file must invalidate the cache, so the zsh directories are watched as well as the files.

## Confirmed decisions

- No TTL fallback; the cache is invalidated by fingerprints only.
- Reset is a shell function (`zsh-recheck`) only, no `machine` subcommand.
- "Healthy" includes the full config loading, not just zsh starting: a plain or partially configured zsh counts as a failure and falls back to bash.

## Open Questions

- The exact hang-guard timeout; about 60 seconds is suggested, not yet confirmed.

## Investigations (not decided, not in the specs)

1. **Fresh-install test with a temporary zinit home.** Suggestion: point zinit at a temporary directory for an explicit `zsh-recheck --fresh` and for tests, so a full fresh install is exercised without touching the real one. Why: it proves a fresh host can install and load completely; it is not suitable as the default check because it re-clones every plugin, needs the network and fails for reasons that do not mean zsh is broken.
