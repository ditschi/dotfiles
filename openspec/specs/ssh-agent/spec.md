# ssh-agent Specification

## Purpose
Defines which SSH agent an interactive bash or zsh uses, and that the dotfiles never start an agent process, so that logins and health-check trials leave no agents behind.

## Requirements

### Requirement: Shells never start an agent
The dotfiles SHALL NOT start an `ssh-agent` process from any shell startup file, in bash or zsh, login or not, including the zsh health-check trial.

#### Scenario: zsh login without an agent
- **WHEN** a zsh login starts with `SSH_AUTH_SOCK` unset and no agent socket provided by the system
- **THEN** no `ssh-agent` process is started and `SSH_AUTH_SOCK` stays unset

#### Scenario: Health-check trial
- **WHEN** the bash-to-zsh health check runs its trial zsh login without `SSH_AUTH_SOCK`
- **THEN** after the trial ends no agent process runs that was not running before

### Requirement: An existing agent socket is kept
When an interactive bash or zsh starts with `SSH_AUTH_SOCK` set, the dotfiles SHALL leave it unchanged, whether it comes from SSH agent forwarding, the desktop session or an earlier shell.

#### Scenario: Forwarded agent over SSH
- **WHEN** the user logs in with `ssh -A` and the remote shell starts with `SSH_AUTH_SOCK` pointing to the forwarded socket
- **THEN** `SSH_AUTH_SOCK` still points to the forwarded socket

#### Scenario: GNOME desktop agent
- **WHEN** a terminal in a GNOME session starts a shell with `SSH_AUTH_SOCK` set by the session
- **THEN** `SSH_AUTH_SOCK` is unchanged

### Requirement: The system agent socket is used
When an interactive bash or zsh starts without `SSH_AUTH_SOCK` and `$XDG_RUNTIME_DIR/openssh_agent` is a socket, the dotfiles SHALL export it as `SSH_AUTH_SOCK`. Without `XDG_RUNTIME_DIR` or without that socket they SHALL set nothing and print nothing.

#### Scenario: Headless host with the systemd socket
- **WHEN** a bash or zsh started over SSH without forwarding finds `$XDG_RUNTIME_DIR/openssh_agent`
- **THEN** `SSH_AUTH_SOCK` is that path in both shells

#### Scenario: Container without a runtime directory
- **WHEN** a shell starts in a container without `XDG_RUNTIME_DIR`
- **THEN** `SSH_AUTH_SOCK` stays unset and nothing is printed
