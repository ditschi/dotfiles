# Spec Delta

## Purpose

Defines which SSH agent an interactive zsh login uses, when the dotfiles start an agent and when they must not, so that logins share one agent instead of leaving a new one behind each time.

## ADDED Requirements

### Requirement: An existing agent socket is kept
When a zsh login starts with `SSH_AUTH_SOCK` set, the dotfiles SHALL leave `SSH_AUTH_SOCK` unchanged and SHALL NOT start an agent, regardless of whether that agent comes from SSH agent forwarding, the desktop session or an earlier shell.

#### Scenario: Forwarded agent over SSH
- **WHEN** the user logs in with `ssh -A` and the remote zsh login starts with `SSH_AUTH_SOCK` pointing to the forwarded socket
- **THEN** `SSH_AUTH_SOCK` still points to the forwarded socket and no agent process is started

#### Scenario: GNOME desktop agent
- **WHEN** a terminal in a GNOME session starts a zsh login with `SSH_AUTH_SOCK` set by the session
- **THEN** `SSH_AUTH_SOCK` is unchanged and no agent process is started

### Requirement: Logins reuse one agent per user
A zsh login without `SSH_AUTH_SOCK` SHALL connect to the agent that the dotfiles or the user's service manager already run for the user at a fixed per-user socket, and SHALL export that socket as `SSH_AUTH_SOCK`. Repeated and concurrent logins SHALL NOT increase the number of agent processes beyond one.

#### Scenario: Second login reuses the agent
- **WHEN** a zsh login without `SSH_AUTH_SOCK` follows an earlier one on the same host while its agent still runs
- **THEN** the new shell's `SSH_AUTH_SOCK` is the same socket and the number of the user's agent processes is unchanged

#### Scenario: Concurrent logins
- **WHEN** two zsh logins without `SSH_AUTH_SOCK` start at the same time and no agent runs yet
- **THEN** afterwards exactly one agent runs and both shells use its socket

### Requirement: An agent is started only when none answers
When no agent answers at the fixed per-user socket, a zsh login SHALL start one agent bound to that socket, replacing a leftover socket file whose agent is gone, and SHALL export the socket. The start SHALL print nothing on success.

#### Scenario: First login after boot
- **WHEN** the first zsh login without `SSH_AUTH_SOCK` starts and no agent runs for the user
- **THEN** one agent is started at the fixed socket, `ssh-add -l` in that shell reaches it, and the login prints no agent output

#### Scenario: Stale socket
- **WHEN** the socket file exists but its agent was killed
- **THEN** the login starts a new agent at the same path and uses it

### Requirement: The zsh health-check trial starts no agent
A zsh login started by the bash-to-zsh health check or by `machine`'s zsh checks (`DOTFILES_ZSH_CHECK` set) SHALL NOT start an agent and SHALL NOT change `SSH_AUTH_SOCK`, so that no agent process outlives the trial.

#### Scenario: Trial start without an agent
- **WHEN** the health check runs its trial zsh login with `SSH_AUTH_SOCK` empty and no agent running
- **THEN** after the trial ends no agent process runs for the user that was not running before

### Requirement: No agent and no error where it cannot run
When `ssh-agent` is not installed or no private per-user runtime directory is available (`XDG_RUNTIME_DIR` unset or not a directory owned by the user), a zsh login SHALL start no agent, leave `SSH_AUTH_SOCK` unset and print nothing.

#### Scenario: Container without openssh-client
- **WHEN** a zsh login starts in a container where `ssh-agent` is missing
- **THEN** the login prints no error and the health check passes

#### Scenario: No runtime directory
- **WHEN** a zsh login starts without `XDG_RUNTIME_DIR`
- **THEN** no agent is started and `SSH_AUTH_SOCK` stays unset
