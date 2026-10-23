# bash-shared-config Specification

## Purpose
Defines which part of the zsh configuration bash shares, so that bash sessions (containers, hosts without zsh, manually started bash) get the same basic environment as zsh.

## Requirements

### Requirement: Shared module subset in bash
An interactive bash session SHALL load the shared modules for aliases, environment, pyenv and history, plus the shared machine profile.

#### Scenario: Interactive bash
- **WHEN** an interactive bash session stays in bash
- **THEN** the alias, environment, pyenv and history modules and the machine profile are loaded

### Requirement: Work modules only on work hosts
bash SHALL load the work modules only when `WORK_SETUP` is `true` and the work module file exists on the host.

#### Scenario: Work machine
- **WHEN** `WORK_SETUP` is `true` and the work module file exists
- **THEN** the work modules are loaded in bash

#### Scenario: Dev container or private host
- **WHEN** `WORK_SETUP` is not `true` or the work module file does not exist
- **THEN** no work module is loaded in bash

### Requirement: Shared modules stay bash-compatible
Every module that bash loads MUST remain valid bash.

#### Scenario: Module loaded by both shells
- **WHEN** a shared module is sourced by bash
- **THEN** it completes without syntax errors

### Requirement: Local bash extension point
`~/.bashrc` SHALL source `~/.bashrc-local` at its end when the file exists, like `~/.zshrc-local` for zsh. Host-specific additions to bash, such as externally managed blocks, live there instead of in the repository file.

#### Scenario: Local file present
- **WHEN** an interactive bash starts and `~/.bashrc-local` exists
- **THEN** it is sourced after the shared configuration

#### Scenario: Local file absent
- **WHEN** `~/.bashrc-local` does not exist
- **THEN** bash starts without error

### Requirement: Bash fallback level
An interactive bash session that stays in bash SHALL provide:
- fzf key bindings and completion (Ctrl+R, Ctrl+T, Alt+C), when fzf is installed
- `z` from zoxide, when zoxide is installed
- LS_COLORS from the zsh plugin checkout, when it exists
- the commands git-open, git-recent and git-recall, when their checkouts exist
- prefix history search on Up/Down
- Esc Esc to prepend `sudo`

bash SHALL NOT load a line-editor replacement such as ble.sh.

#### Scenario: bash on a host with the tools
- **WHEN** an interactive bash starts on a host with fzf, zoxide and the zsh plugin checkout
- **THEN** Ctrl+R opens fzf, `z` works, `ls` uses the LS_COLORS colours, and `git recent` is found

#### Scenario: bash on a host without the tools
- **WHEN** an interactive bash starts on a host without fzf, zoxide or the zsh plugin checkout
- **THEN** bash starts without error output and the missing parts are absent

#### Scenario: Startup time
- **WHEN** an interactive bash starts on the reference host with every tool installed
- **THEN** the first prompt appears in under 70 ms

### Requirement: Paste support in bash
In bash, a command line starting with `❯ ` SHALL run the rest of the line. A line starting with `$ ` SHALL run the rest of the line in a subshell, so directory changes made this way do not persist.

#### Scenario: Pasted line with the prompt character
- **WHEN** the user runs `❯ echo hi` in bash
- **THEN** `hi` is printed

#### Scenario: Pasted line with a dollar sign
- **WHEN** the user runs `$ echo hi` in bash
- **THEN** `hi` is printed
