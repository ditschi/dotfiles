# Proposal

## Why

`~/.zprofile` starts a new `ssh-agent` at every zsh login that finds `SSH_AUTH_SOCK` empty and never stops it. Every such login therefore leaves an agent process behind, including each trial start of the bash-to-zsh health check (`DOTFILES_ZSH_CHECK=1`), whose cleanup cannot catch the agent because it detaches itself. The agent holds no keys: the keys have no passphrase and `AddKeysToAgent` is not set (`openspec/backlog.md`, "SSH agent forwarding for trusted hosts").

On 2026-11-08 the owner decided that the shells never start an agent themselves: they keep an existing `SSH_AUTH_SOCK`, otherwise point it at the agent socket the system provides, otherwise use no agent, and bash and zsh behave the same.

## What Changes

- **BREAKING** (for hosts without a system agent socket): `~/.zprofile` no longer starts `ssh-agent`. A login that relied on that agent, for example for `ssh-add` on a headless host, has no agent unless the host provides one.
- An interactive bash or zsh with `SSH_AUTH_SOCK` set (agent forwarding over SSH, the GNOME session's agent) keeps it unchanged, as today.
- An interactive bash or zsh without `SSH_AUTH_SOCK` exports `$XDG_RUNTIME_DIR/openssh_agent` when that socket exists. It belongs to the systemd user unit `ssh-agent.socket` shipped by `openssh-client`; systemd starts one agent per user on first use and stops it.
- Otherwise the shell sets nothing and prints nothing.
- `docs/ssh.md` describes which agent a shell uses and how to end agents left by earlier logins.
- Unchanged: `ssh-client-config` still sets neither `ForwardAgent` nor `AddKeysToAgent`.

## Capabilities

### New Capabilities

- `ssh-agent`: which SSH agent an interactive shell uses, and that the dotfiles never start one.

### Modified Capabilities

None. No current spec covers `~/.zprofile` or the agent (`zsh-config-loading` covers the interactive module loader, `shell-handoff` the bash-to-zsh check, `ssh-client-config` the client config).

## Impact

- Code: `home/core/.zprofile` (agent block removed), `home/core/.shell/common/environment.sh` (shared by the interactive bash and zsh loaders).
- Consumers: the health check in `home/core/.shell/bash/zsh-health.bash` and `machine`'s zsh checks run `zsh -l -i` and load both files; with no agent start, no process outlives a trial. `.zprofile` is a watched file there, so the change re-runs the check once.
- Tests: new `tests/unit/test_ssh_agent.py`.
- Docs: `docs/ssh.md`.
- Related backlog: "SSH agent forwarding for trusted hosts" decides later which agent holds the key; this change only decides which agent a shell talks to.
- Profiles: every host with the core dotfile group - private and work, desktop, server and container - including the work VM.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/ssh-agent-reuse` on branch `ssh-agent-reuse`, because the change edits files the host's shells read directly from the live checkout.
