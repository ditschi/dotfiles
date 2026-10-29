# Spec Delta

## ADDED Requirements

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
