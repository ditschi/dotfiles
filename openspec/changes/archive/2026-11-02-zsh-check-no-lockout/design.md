# Design

## Context

See proposal.md for the motivation and specs/shell-handoff/spec.md for the required behaviour.

`home/core/.shell/bash/zsh-health.bash` starts the trial as `timeout --foreground -k 1 ${DOTFILES_ZSH_CHECK_TIMEOUT:-60} zsh -l -i -c ...`. Its output goes to temporary files, and its stdin is `/dev/tty` when bash has a terminal. The archived `2026-10-22-add-zsh-startup-check/design.md` chose this because an interactive zsh without a terminal printed harmless errors (zle, monitor, gitstatus), and `--foreground` keeps terminal access from stopping the trial. Decision 8 there makes the timeout a generous hang guard that is never cached.

Evidence gathered for this change (2026-11-02):

- **The lockout reproduces.** A PTY reproduction (interactive bash, a stub zsh that starts a process reading `/dev/tty` and then sleeps, timeout 2 s) shows the bash prompt, but typed lines are split between bash and the leftover process. One command arrived as `c Eecho TYPED1` (`command not found`), and the leftover process recorded `ehoTYPD0`. This matches the owner's report: the SSH login appeared stuck and input went astray.
- **The cause is `--foreground`.** `timeout --foreground` does not time out the children of the command, and the trial shares bash's terminal. A child that waits for terminal input therefore stays and competes with bash for keystrokes.
- **The same reproduction with the trial detached passes.** With the trial run as `setsid -w timeout -k 1 <secs> zsh ...` and stdin from `/dev/null`, bash ran all three typed commands and nothing else read them.
- **The archived reason no longer applies.** The real config started detached with `DOTFILES_ZSH_CHECK=1`, `TERM` set and stdin `/dev/null`:
  - development desktop: exit 0, 0.26 s, `DOTFILES_ZSH_LOADED=1 DOTFILES_ZSH_DEFERRED_LOADED=1`, no error output;
  - affected work VM (ABTVL421): exit 0, the same markers, no error output.
- **`machine` already checks without a terminal.** Its post-update and auto-update checks (`zsh_health_failure` in `machine_cli/auto_update.py`) call `_zhc_run_checks` from a non-terminal process with stdin `/dev/null`, and they pass on these hosts.
- **The VM has system login hooks that can wait for input.** `/etc/profile.d` hooks there run `sudo systemctl restart ...`, and sssd refused connections during an earlier boot. Such a hook would wait for a password on the terminal, which is exactly the kind of startup step that blocked the trial.

## Goals / Non-Goals

**Goals:**
- A trial zsh start can never take terminal input from the session that runs the check.
- A timed-out or interrupted trial leaves no process attached to it.
- The handoff, its diagnostics and its cache behave as before in every other respect.

**Non-Goals:**
- Changing the timeout length or caching timeouts (decision 8 of the archived design stays).
- Changing which output counts as a failure (see Open Questions).
- Fixing the system login hooks, the ssh-agent started per login, or the VS Code Remote-SSH problems on the work VM; these are separate changes.

## Decisions

1. **Run the trial in its own session without the terminal.** The check runs the trial as `setsid -w <timeout> zsh -l -i -c ...` with stdin `/dev/null`. In a new session, `/dev/tty` cannot be opened, so no startup step can read the user's terminal. `-w` keeps the check waiting for the exit status.
   - Rejected: keeping the terminal on stdin and killing the process group on timeout. Until the timeout, a child would still read keystrokes, and an interactive zsh with job control moves itself into its own process group anyway.
   - Rejected: stdin `/dev/null` without a new session. An interactive zsh, or a child such as `sudo`, can still open `/dev/tty` through the controlling terminal.
2. **Drop `--foreground` and use plain `timeout -k 1 <secs>` inside the new session.** Without `--foreground`, `timeout` signals the whole process group of the command when the time runs out, so the children of the trial end too. `-k 1` stays, because an interactive zsh ignores `SIGTERM`. Daemons that detach themselves (for example `ssh-agent` from `~/.zprofile`) are not part of the group and stay. They have no terminal and cannot read input.
3. **Ctrl-C ends the trial and stays in bash.** The trial runs in another session, so Ctrl-C at the terminal reaches only bash. The check traps `INT` while it waits: it signals the trial's process group, reports "zsh check interrupted", caches nothing and returns failure, so the session stays in bash and the rest of `~/.bashrc` still runs. The calling bash also sets a no-op `INT` trap around the check, because an interactive bash otherwise skips the rest of `~/.bashrc` on Ctrl-C (verified in a PTY test).
4. **Fallback without `setsid`.** `setsid` comes from util-linux, which is essential on the supported distributions. If it is missing anyway, the trial runs without a new session, with stdin `/dev/null` and plain `timeout`. That still keeps the trial off the terminal's stdin and kills its process group, just without the `/dev/tty` guarantee.
5. **No change for `machine`'s checks.** They call the same `_zhc_run_checks` and already run without a terminal. They get the process cleanup for free.

## Risks / Trade-offs

- [A zsh startup step behaves differently without a terminal and prints an error, causing a false failure] → Verified clean on the desktop and the work VM. A failure is cached with its reason and the error line, and `zsh-recheck` re-runs the check after a fix.
- [`$TTY`-guarded integrations (for example the fzf key bindings) are skipped during the trial and stay untested] → That code path already works this way for `machine`'s checks; the real handoff loads them with a terminal.
- [The `INT` trap leaks into the rest of `~/.bashrc`] → The trap is set only around the wait and the previous trap is restored afterwards.

## Migration Plan

Nothing to migrate. Changing `zsh-health.bash` invalidates the cached outcome (the helper is a watched file), so the next interactive bash start runs the new check once. Rollback is a dotfiles update that reverts the file.

Decisions 1–5 were confirmed by the owner on 2026-11-02. They replace the archived choice to keep the terminal and use `--foreground` (`2026-10-22-add-zsh-startup-check/design.md`, Risks).

The owner also kept decision 8 of that design: a timeout stays uncached. A hang no longer takes the user's input; it costs one wait per login that Ctrl-C can skip. Caching it would keep a host in bash longer after the cause is fixed.

## Open Questions

- A system login hook on the work VM printed `Kerberos token invalid, refreshing...` to stderr during a trial, so zsh was cached as failed until the next check. Should error output be tolerated when the dotfiles config loaded completely? That would change the "Handoff health check" requirement, so it belongs in a separate change.
