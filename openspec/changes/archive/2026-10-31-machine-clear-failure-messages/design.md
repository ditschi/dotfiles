# Design

## Context

- `cmd_apply` (`machine_cli/commands.py`) runs Ansible and then `health_check_after_apply()` inside one `try`. Both failures land in the same `except`, which, when the host config was unchanged, logs "Review Ansible's error; sudo command restrictions require administrator approval, not a different password." That is correct for a failed Ansible run and wrong for a failed health check.
- `health_check_after_apply()` (`machine_cli/tools.py`) collects `zsh_health_failure()` and `dotfiles_health_failure()`. zsh counts as unhealthy when its startup prints anything on stderr, which includes mise's `mise WARN missing: <tool>` for a configured tool that is not installed. `machine apply` does not run `mise install`; only `machine update` does, before the apply step.
- For a diverged history, `rebase_blocker()` (`machine_cli/local_work.py`) returns only a reason string. When uncommitted changes overlap the incoming commits and a trial merge conflicts, the reason is "uncommitted local changes conflict with the incoming ones", and `blocked_reason()` turns it into "… → run: git pull --rebase, then machine". `git pull --rebase` refuses to run while those changes exist. The existing conflict dialog (`resolve_conflicts`, `stash_conflicts`, `show_conflict_diff`) is only used when the history is behind, not diverged.
- `system.have()` is `shutil.which()`. Over `ssh host command` zsh is not a login shell, so `~/.local/bin` (where `mise`, `bw` and `machine` itself live) is not in `PATH`.

## Goals / Non-Goals

**Goals:**
- Each failure message names the step that failed and a next step that works in that state.
- The diverged case reuses the existing conflict choices instead of adding a new dialog.

**Non-Goals:**
- Making `machine` itself callable as a bare command over `ssh host command`; the Readme shows the full path `~/.local/bin/machine`.
- Changing what the zsh health check counts as a failure.
- New blockers or new rebase rules; the conditions of "Clean rebase of local commits" stay as they are.

## Decisions

**Separate the two failing steps in `cmd_apply`.** Ansible and the health check get their own failure reasons. The rollback is the same for both; only the message differs. The Ansible/sudo hint is printed only for a failed Ansible run. A failed health check prints "health check failed after the apply: <reason>" and, for missing mise tools, "run: mise install".

**One `mise install` before rolling back for missing tools.** When the zsh failure is a `mise WARN missing: …` line (the zsh check reports only the first error line, so any other error shows up in the repeated check), `machine` logs that it installs the missing tools, runs `mise install` once (same environment and working directory as the tool-install step of `machine update`), and repeats the health check. Rejected: installing silently inside the check, because a check should report rather than repair and a silent repair would hide that the install path (for example a stale lock) is broken; counting missing tools as no failure, because the shell then really lacks a tool. Restricting the retry to this exact message keeps network access and long installs out of every other failure.

**The diverged case uses the conflict choices.** `rebase_blocker()` additionally reports the conflicting uncommitted files. When that is the only blocker, `machine update` treats it like a conflict while behind: on a terminal it shows the diff and offers resolve manually (default) or stash; `--force` takes the stash. The stash choice puts only the conflicting files into a named stash entry (with its attention item), then runs the existing `rebase_keeping_local()`, which keeps the remaining uncommitted changes. Without a terminal, or when the user resolves manually, the reason names the files, the local and incoming commit counts, and says "commit, stash or discard them, then run: machine update". Rejected: only rewording the message, because the stash path already exists and handles exactly this case for a behind checkout.

**`machine` puts `~/.local/bin` on `PATH` at start.** If `~/.local/bin` is not in `PATH`, the CLI entry point prepends it before anything else runs, so `system.have()` and every subprocess (mise, bw, ansible) see the same tools as in a login shell. Rejected: checking only `~/.local/bin/mise` in the not-set-up test, because `bw` and other tools would still be missing in the same situation.

## Risks / Trade-offs

- [`mise install` during an apply needs network and can take a while] → it runs only when the health check fails solely because of missing mise tools, and it is logged before it starts.
- [Prepending `~/.local/bin` can shadow a system binary of the same name] → this is the same order a login shell uses on these hosts; it changes nothing for runs that already have it in `PATH`.
- [The trial merge that finds conflicting files can disagree with the real rebase] → the stash path already falls back to stopping with the stash entry kept (`rebase_keeping_local` restores and warns), so nothing is lost.

## Migration Plan

No migration. Rollback: revert the commits; the old messages return.
