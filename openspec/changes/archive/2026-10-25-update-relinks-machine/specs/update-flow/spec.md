# Spec Delta

## MODIFIED Requirements

### Requirement: Update ends converged
`machine update` SHALL end with a converge check, also when nothing was incoming: the user-space tools declared in the `mise` configuration are installed (missing ones are added), the dotfile groups of the host are applied (missing links created, removed ones pruned), `~/.local/bin/machine` is a symlink to the CLI script of the checkout that runs, and, when the command runs in an interactive shell, that shell is replaced by a fresh one so the result is live without opening a new terminal. The checks SHALL be idempotent and cheap when nothing is missing.

#### Scenario: Nothing incoming but a tool is missing
- **WHEN** a user runs `machine update`, no commits are incoming and a declared tool is not installed
- **THEN** the tool is installed

#### Scenario: Link missing
- **WHEN** a user runs `machine update` and a dotfile link of the host's groups is missing
- **THEN** the link is created

#### Scenario: Entry point of the earlier layout
- **WHEN** `~/.local/bin/machine` is a regular file and a user runs `~/dotfiles/machine_cli/machine update`
- **THEN** it is replaced by a symlink to `machine_cli/machine` in the checkout and `machine` starts again

#### Scenario: Fresh shell after the update
- **WHEN** `machine update` finishes successfully in an interactive shell
- **THEN** that shell is replaced by a freshly loaded one; a failed update leaves the shell untouched
