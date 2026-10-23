## ADDED Requirements

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
