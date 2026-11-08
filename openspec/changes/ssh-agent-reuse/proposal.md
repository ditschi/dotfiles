# Proposal

## Why

`~/.zprofile` starts a new `ssh-agent` at every zsh login that finds `SSH_AUTH_SOCK` empty and never stops it. Every such login therefore leaves an agent process behind, including each trial start of the bash-to-zsh health check (`DOTFILES_ZSH_CHECK=1`), whose cleanup cannot catch the agent because it detaches itself. The owner decided on 2026-11-08 that logins reuse one agent instead of starting one each, and that the health-check trial starts no agent at all.

## What Changes

- A zsh login without `SSH_AUTH_SOCK` connects to an agent that is already running for the user and starts one only when none answers; repeated logins no longer add agent processes.
- A login that already has `SSH_AUTH_SOCK` (agent forwarding over SSH, GNOME's agent) keeps it unchanged, as today.
- The health-check trial start (`DOTFILES_ZSH_CHECK=1`), which also covers `machine`'s post-update and auto-update zsh checks, starts and exports no agent.
- Hosts without `ssh-agent` (minimal containers) or without a usable per-user runtime directory get no agent and no startup error output (behaviour without `XDG_RUNTIME_DIR` is an open question in design.md).
- `docs/ssh.md` describes which agent a shell uses.
- Unchanged: bash starts no agent (neither `~/.profile` nor `~/.bashrc` nor `~/.shell/bash` does today); `ssh-client-config` still sets neither `ForwardAgent` nor `AddKeysToAgent`.

## Capabilities

### New Capabilities

- `ssh-agent`: which SSH agent an interactive login shell uses, when the dotfiles start one, and when they must not.

### Modified Capabilities

None. No current spec covers `~/.zprofile` or the agent (`zsh-config-loading` covers the interactive module loader, `shell-handoff` the bash-to-zsh check, `ssh-client-config` the client config). The health-check exclusion is specified in `ssh-agent`, so `shell-handoff` requirements stay as they are.

## Impact

- Code: `home/core/.zprofile` (agent block, lines 11-14); optionally a small shared helper if the design moves the logic out of `.zprofile`.
- Consumers: the health check in `home/core/.shell/bash/zsh-health.bash` and `machine`'s zsh checks (they run `zsh -l` with `DOTFILES_ZSH_CHECK=1`); `.zprofile` is a watched file there, so the change re-runs the check once.
- Tests: new unit tests (e.g. `tests/unit/test_ssh_agent.py`) that run `.zprofile` with a scratch `HOME` and `XDG_RUNTIME_DIR`.
- Docs: `docs/ssh.md`.
- Related backlog: "SSH agent forwarding for trusted hosts" in `openspec/backlog.md` asks which agent holds the key on desktop and headless hosts; this change decides which agent a shell talks to but adds no keys and no forwarding.
- Profiles: every host with the core dotfile group - private and work, desktop, server and container - including the work VM, where bash hands over to zsh.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/ssh-agent-reuse` on branch `ssh-agent-reuse`, because the change edits `~/.zprofile`, which the host's login shells read directly from the live checkout.
