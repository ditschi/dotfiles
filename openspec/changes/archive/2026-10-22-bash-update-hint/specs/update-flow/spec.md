## MODIFIED Requirements

### Requirement: Update hint at shell start
When the marker file `~/.dotfiles-update-available` exists, a new interactive zsh or bash SHALL print "Hint: Dotfiles update available (run: machine update)". The shell SHALL NOT run the update check itself, so that startup stays fast.

#### Scenario: Update available
- **WHEN** the marker exists and a zsh starts
- **THEN** the hint is printed

#### Scenario: Update available in bash
- **WHEN** the marker exists and an interactive bash starts and stays in bash
- **THEN** the hint is printed once

#### Scenario: No update
- **WHEN** the marker does not exist
- **THEN** no hint is printed
