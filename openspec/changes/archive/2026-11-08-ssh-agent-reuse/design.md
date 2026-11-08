# Design

## Context

See proposal.md - Why. Current state, checked read-only on the owner's desktop (Ubuntu 26.04, 2026-11-08):

- `home/core/.zprofile` runs `eval "$(ssh-agent -s)"` when `SSH_AUTH_SOCK` is empty. Bash starts no agent. Nothing in the repository reads `SSH_AGENT_PID`.
- The health check (`zsh-health.bash`) runs `zsh -l -i -c ...` with `DOTFILES_ZSH_CHECK=1` and kills its process group on exit; the agent daemonises out of that group and stays (archived `2026-11-02-zsh-check-no-lockout/design.md`, decision 2). The background `machine update` runs the check with the systemd user manager's environment.
- `openssh-client` ships `/usr/lib/systemd/user/ssh-agent.socket` (`ListenStream=%t/openssh_agent`, mode `0600`), enabled by preset; it sets `SSH_AUTH_SOCK` only in the user manager's environment, which SSH logins do not import. `/run/user/1000/openssh_agent` exists on the desktop.
- `gcr4` provides `gcr-ssh-agent.socket` (`$XDG_RUNTIME_DIR/gcr/ssh`); the GNOME session and the user manager export it as `SSH_AUTH_SOCK`.
- `XDG_RUNTIME_DIR` is set by `pam_systemd` (`/etc/pam.d/common-session`) for every console, GUI and SSH login and by the user manager for its services; it is missing in containers without systemd and in `su`/`sudo -u` shells.
- Keys have no passphrase and `AddKeysToAgent` is unset, so `ssh` reads the key files directly and needs no agent today.

## Goals / Non-Goals

**Goals:** no agent process caused by the dotfiles; an agent where the system provides one; the same behaviour in bash and zsh.

**Non-Goals:** loading keys, `AddKeysToAgent`, `ForwardAgent` (backlog item on agent forwarding); enabling or masking systemd user units; killing agents earlier logins left behind.

## Decisions

### The shells never start an agent (owner decision 2026-11-08)
An agent is only useful for keys with a passphrase and for forwarding; neither applies today. The desktop session and the systemd socket already provide one agent per user that the system starts and stops. Starting our own agent only adds processes that nobody stops.

Alternatives considered: reusing one own agent at a fixed socket in `XDG_RUNTIME_DIR` (needs stale-socket handling, a race guard and a health-check exception, and can run next to the systemd agent); removing the agent start without using the systemd socket (headless hosts would lose an agent the system offers for free).

### Use the systemd socket only when `SSH_AUTH_SOCK` is unset
An existing value is never overridden, so forwarding and the GNOME agent keep working. Without `XDG_RUNTIME_DIR` there is no safe per-user place for a socket, so nothing is done (owner decision 2026-11-08); this needs no separate branch, because the socket test fails.

### The logic lives in `environment.sh`
`home/core/.shell/common/environment.sh` is loaded by both interactive loaders (`bash/init.bash`, `zsh/init.zsh`), so bash and zsh behave the same with one copy of the code. `~/.profile` is not used, because display managers may source it before the session exports its own agent, and the shell could then override gcr (not verified; avoided by staying in the interactive loaders). Non-interactive `ssh host cmd` gets no agent, as today.

## Risks / Trade-offs

- [A headless host without `ssh-agent.socket` (older OpenSSH, unit disabled) has no agent any more] → keys without passphrase work without one; `eval "$(ssh-agent -s)"` by hand still works; the docs say so.
- [The systemd socket exists but the user manager stopped] → the socket file is removed with the unit, so the test fails and nothing is set.

## Migration Plan

`machine update` brings the new files; the health check re-runs once because `.zprofile` is watched. Agents left by earlier logins keep running until reboot or until ended by hand (`docs/ssh.md`); the change does not kill them, because a running shell may still use one. Rollback: revert the commit.
