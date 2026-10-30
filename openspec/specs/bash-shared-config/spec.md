# bash-shared-config Specification

## Purpose
Defines which part of the zsh configuration bash shares, so that bash sessions (containers, hosts without zsh, manually started bash) get the same basic environment as zsh.

## Requirements

### Requirement: Shared module subset in bash
An interactive Bash session that stays in Bash SHALL load aliases, environment and machine-profile modules from `~/.shell/common`, with Bash-specific history and integration from `~/.shell/bash`, through an explicit ordered source list in `~/.shell/bash/init.bash`. Startup SHALL NOT automatically execute unregistered files. Non-interactive Bash SHALL return before loading the interactive configuration.

#### Scenario: Interactive bash
- **WHEN** an interactive bash session stays in bash
- **THEN** the shared alias, environment and machine-profile modules and the Bash-specific history module are loaded in the declared order
- **AND** registered modules execute once per startup without loading zsh-only code

#### Scenario: Unregistered file
- **WHEN** an additional file exists in a shell module directory but is not registered in the load sequence
- **THEN** Bash startup does not execute that file

#### Scenario: Non-interactive bash
- **WHEN** a non-interactive Bash process sources `~/.bashrc`
- **THEN** it returns before loading the interactive modules or running the shell handoff

### Requirement: Work modules only on work hosts
Bash SHALL load shared work modules from `~/.shell/work/common` only when `WORK_SETUP` is `true` and the work module files exist on the host. Work tools SHALL load before the work environment that depends on them. Bash SHALL NOT load zsh-only work helpers.

#### Scenario: Work machine
- **WHEN** `WORK_SETUP` is `true` and the work module files exist
- **THEN** the work tools and work environment modules are loaded in bash, in that order

#### Scenario: Dev container or private host
- **WHEN** `WORK_SETUP` is not `true` or the work module files do not exist
- **THEN** no work module is loaded in bash

#### Scenario: Zsh-only work helper
- **WHEN** shared work modules are loaded in Bash
- **THEN** the LDAP helpers under `~/.shell/work/zsh` are not loaded

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

### Requirement: Failed-command duplicate-prefix suggestion in bash
Interactive bash SHALL execute the original submitted command before considering duplicate-prefix cleanup. If it fails and begins with adjacent repeated words, bash SHALL offer a cleaned command in the editable prompt, removing one copy of the repeated prefix. The cleaned command SHALL NOT execute without user confirmation. Successful commands SHALL NOT trigger cleanup.

#### Scenario: Repeated command word fails
- **WHEN** `git git status` fails in interactive bash
- **THEN** the next editable command line contains `git status`
- **AND** `git status` has not been executed

#### Scenario: Repeated multiword prefix fails
- **WHEN** `git remote git remote -v` fails in interactive bash
- **THEN** the next editable command line contains `git remote -v`
- **AND** the user can edit, discard or submit it

#### Scenario: Successful command contains repeated leading words
- **WHEN** a command with repeated leading words succeeds
- **THEN** bash does not offer a deduplicated command

#### Scenario: Failed command has no repeated prefix
- **WHEN** a command fails without adjacent repeated leading words
- **THEN** the duplicate-prefix helper does not change the next command line
