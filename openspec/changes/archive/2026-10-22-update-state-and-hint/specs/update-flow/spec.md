## MODIFIED Requirements

### Requirement: Update hint at shell start
Interactive zsh and bash SHALL show the update state as a persistent prompt segment: update available, updated and shell reload needed, or needs attention. A shell started after the update was applied SHALL show nothing. At shell start a one-line message SHALL be printed only for needs-attention. The segment SHOULD follow state changes in an open shell, re-evaluated after each command without reloading the shell, as long as this stays lightweight and the prompt stays fast. The shell SHALL NOT run the update check itself, so that startup stays fast.

#### Scenario: Update available
- **WHEN** an update is pending and not applied automatically and a zsh starts
- **THEN** the prompt segment shows that an update is available and no text is printed at shell start

#### Scenario: Update available in bash
- **WHEN** an update is pending and not applied automatically and an interactive bash starts and stays in bash
- **THEN** the prompt segment shows that an update is available

#### Scenario: Shell older than the applied update
- **WHEN** an update was applied after the shell started
- **THEN** the prompt segment tells the user to reload the shell

#### Scenario: Needs attention
- **WHEN** the update needs manual checking
- **THEN** the prompt segment shows it and a one-line message is printed at shell start

#### Scenario: No update
- **WHEN** no update is pending and the shell is current
- **THEN** nothing is shown

#### Scenario: State changes in an open shell
- **WHEN** the update state changes while a shell is open
- **THEN** the prompt segment shows the new state after the next command
