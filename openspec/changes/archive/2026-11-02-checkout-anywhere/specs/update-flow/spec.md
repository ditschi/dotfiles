# Spec Delta

## MODIFIED Requirements

### Requirement: Compact status
`machine status` SHALL show a short overview with one line per topic and the features in columns. It SHALL use colors only on a terminal and honor `NO_COLOR`. `machine status -v` SHALL also show the full host config, the dotfile groups configuration and the file lists.

#### Scenario: Default status
- **WHEN** a user runs `machine status` in a terminal
- **THEN** it shows the path of the checkout it operates on, the branch and how far it is behind, the time of the last check, the attention reason with the next command, the incoming change count with the steps, counts of local changes, one host line (name, context, device, host config in sync), the features in columns and the dotfile groups on one line, and does not print the host config or the dotfile groups configuration in full

#### Scenario: Verbose status
- **WHEN** a user runs `machine status -v`
- **THEN** the full host config, the dotfile groups configuration and the lists of local and incoming files are shown as well

#### Scenario: Stash entries put aside by machine
- **WHEN** the stash holds entries that `machine` created, recorded in the update state or recognised by their name `machine update <date>: <why>`
- **THEN** the status shows how many there are and that the user decides in `machine attention` whether to restore or drop them; `-v` lists them; stash entries the user made are not counted

#### Scenario: Piped status
- **WHEN** the output of `machine status` is not a terminal or `NO_COLOR` is set
- **THEN** no color codes are written
