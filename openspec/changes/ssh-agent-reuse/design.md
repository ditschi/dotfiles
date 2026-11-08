# Design

## Context

See proposal.md - Why. Current state, checked read-only on the owner's desktop (Ubuntu 26.04, 2026-11-08):

- `home/core/.zprofile` lines 11-14 run `eval "$(ssh-agent -s)"` when `SSH_AUTH_SOCK` is empty. `.zprofile` is read only by zsh login shells; on the work VM that is the handoff `exec zsh -l` from bash. Bash itself starts no agent (`~/.profile`, `~/.bashrc` and `~/.shell/bash` contain no agent code). Nothing in the repository reads `SSH_AGENT_PID`.
- The health check (`zsh-health.bash`) runs `zsh -l -i -c ...` with `DOTFILES_ZSH_CHECK=1` in its own session and kills the process group on exit; the agent daemonises out of that group and stays (archived `2026-11-02-zsh-check-no-lockout/design.md`, decision 2). It inherits the caller's environment, so it leaks an agent whenever the caller has no `SSH_AUTH_SOCK` (SSH login without forwarding, background `machine update`).
- `openssh-client` ships `/usr/lib/systemd/user/ssh-agent.socket` and `ssh-agent.service`. The socket listens on `%t/openssh_agent` (= `$XDG_RUNTIME_DIR/openssh_agent`), is `enabled` with preset `enabled` on this host, and only sets `SSH_AUTH_SOCK` in the systemd user manager's environment (`systemctl --user set-environment`), which SSH logins do not import.
- `gcr4` ships `gcr-ssh-agent.socket` (`$XDG_RUNTIME_DIR/gcr/ssh`), enabled here; the GNOME session exports it as `SSH_AUTH_SOCK`. On this desktop the shells therefore already have an agent and the `.zprofile` block does nothing; three agent-named processes run, all owned by systemd or gcr, none leaked.
- Keys have no passphrase and `AddKeysToAgent` is unset (`ssh-client-config`), so the agent normally holds no keys; its users are explicit `ssh-add` and the planned agent forwarding (backlog "SSH agent forwarding for trusted hosts").
- Containers (`project-containers`, device `container`) have no systemd user instance and often no `XDG_RUNTIME_DIR`; extended containers mount the host `$HOME`.

## Goals / Non-Goals

**Goals:**
- At most one agent per user and host that the dotfiles cause, whatever the number of logins.
- Pure POSIX `sh` in `.zprofile`, no dependency on systemd, so the same code works on desktops, headless servers, the work VM and containers.

**Non-Goals:**
- Loading keys into the agent, `AddKeysToAgent`, `ForwardAgent` or confirm-on-use; those stay with the backlog item on agent forwarding.
- Killing agents that earlier logins already left behind (see Migration Plan).
- Starting an agent in bash.
- Managing systemd user units (enabling, disabling or masking `ssh-agent.socket` or `gcr-ssh-agent.socket`).

## Decisions

1. **Keep an existing `SSH_AUTH_SOCK`.** A set variable is never overridden, so forwarding over SSH and GNOME's agent keep working.
2. **Reuse one agent instead of one per login.** A login without `SSH_AUTH_SOCK` connects to a running agent and starts one only when none answers.
3. **No agent in the health-check trial.** With `DOTFILES_ZSH_CHECK` set, the agent block returns before doing anything. This also covers `machine`'s checks, which call the same function.

## Proposed approach (pending owner confirmation)

The mechanism is not decided by the owner yet (see Open Questions, Q1). Recommended, in this order inside the `.zprofile` block:

1. `SSH_AUTH_SOCK` set, or `DOTFILES_ZSH_CHECK` set → do nothing.
2. `ssh-agent` not on `PATH`, or `XDG_RUNTIME_DIR` unset / not a directory owned by the user → do nothing (Q3).
3. If `$XDG_RUNTIME_DIR/openssh_agent` is a socket (systemd `ssh-agent.socket`), export it. Socket activation starts the agent on first use; the systemd user manager owns and stops it.
4. Otherwise use the fixed path `$XDG_RUNTIME_DIR/ssh-agent.socket`: probe it with `SSH_AUTH_SOCK=<path> ssh-add -l` (exit 2 = no agent answers; 0 or 1 = alive). If dead, remove the file and run `ssh-agent -a <path> >/dev/null`; if that fails because a concurrent login bound the path first, use the path anyway. Export `SSH_AUTH_SOCK=<path>`; `SSH_AGENT_PID` is not exported.

Alternatives evaluated:

- **Fixed socket only** (`ssh-agent -a "$XDG_RUNTIME_DIR/ssh-agent.socket"` when dead, step 4 alone). Works everywhere with `XDG_RUNTIME_DIR`, no systemd dependency. On hosts where `ssh-agent.socket` is enabled by preset it adds a second, redundant agent next to the systemd one; the agent outlives logouts until the runtime directory is removed (with linger, until reboot).
- **systemd user units only** (`ssh-agent.socket`, shipped by `openssh-client` on this Ubuntu 26.04 host). One agent managed and stopped by systemd, no stale-socket handling. Does not work in containers or where the user manager does not run, and the work VM's release may not ship the units (Q2); the shell still has to export the socket for SSH logins, so a fallback is needed anyway.
- **GNOME `gcr-ssh-agent.socket`.** Only present with a desktop session and gcr4; GNOME already exports it, so decision 1 covers it. Not usable on headless hosts, the work VM or containers.

The recommended order combines the second option where it exists with the first as fallback; the shell code is the same on every host.

## Risks / Trade-offs

- [The fixed-socket agent outlives every shell and accumulates keys added with `ssh-add` for the whole uptime] → Same as the systemd unit; keys have no passphrase and none are added automatically today.
- [A dead agent leaves its socket file; a naive `ssh-agent -a` then fails with "Address already in use"] → Probe with `ssh-add -l` and remove the file only when the probe reports no connection.
- [Race between two logins] → `ssh-agent -a` binds atomically; the loser fails silently and uses the winner's socket.
- [`ssh-add -l` hangs on a wedged agent and delays the login] → Bounded by the health check's timeout during the trial; risk accepted for the real login, as the agent is local.
- [Extended containers mount the host `$HOME`] → The socket lives in `XDG_RUNTIME_DIR`, not in `$HOME`, so containers neither see nor reuse the host agent.

## Migration Plan

`machine update` brings the new `.zprofile`; the health check re-runs once because `.zprofile` is watched. Agents left by earlier logins keep running until reboot or until the owner ends them by hand (for example `pgrep -u "$USER" -ax ssh-agent` to list, then `kill` the ones not owned by systemd or gcr); the change does not kill them, because a running shell may still use one. Rollback is a dotfiles update that reverts `.zprofile`.

## Open Questions

- **Q1 - Mechanism.** Recommendation: the order in "Proposed approach" (systemd `openssh_agent` socket if present, else fixed socket in `XDG_RUNTIME_DIR`). Alternatives: fixed socket only (simplest, possibly one redundant agent), systemd only (fails in containers).
- **Q2 - Work VM.** Unknown whether a local agent is needed there at all (Remote-SSH may forward one) and whether its OpenSSH ships `ssh-agent.socket`. Recommendation: before implementing, run in a Remote-SSH terminal and in a plain SSH login on the work VM: `echo "$SSH_AUTH_SOCK"`, `pgrep -u "$USER" -ax ssh-agent` (note that `pgrep -c ssh-agent` also counts `gcr-ssh-agent`), `ls /usr/lib/systemd/user/ | grep -i agent`, `systemctl --user is-enabled ssh-agent.socket`. If an agent is never used there, the same code still applies; no work-only exception is recommended.
- **Q3 - No `XDG_RUNTIME_DIR`.** Today such a login gets a per-login agent. Recommendation: start none (as in the spec), because a fallback in `/tmp` needs ownership checks and keys are not loaded automatically anyway. Alternatives: keep a per-login agent there, or a private `/tmp/ssh-agent-<uid>/` directory. If the owner picks an alternative, the requirement "No agent and no error where it cannot run" changes.
- **Q4 - Bash.** Recommendation: leave bash without an agent, as today; bash sessions that need one hand over to zsh or set it up by hand. Alternative: move the block into a shared POSIX file read by both `.zprofile` and `.profile`.
