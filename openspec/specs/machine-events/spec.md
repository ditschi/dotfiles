# machine-events Specification

## Purpose
Keep a small local log of what `machine` did automatically (auto-update, manual update, reverts) so a user can see afterwards what changed on this host and why.

## Requirements

### Requirement: Local event log
The `machine` CLI SHALL append one JSON line per notable event to `events.jsonl` in the machine state directory, only with timestamp, event, outcome, reason code, duration, short revision and profile. The file SHALL stay on the host and writing SHALL be best effort.

#### Scenario: Automatic update is reverted
- **WHEN** the automatic update reverts after a failed zsh health check
- **THEN** an event with the outcome `reverted` and the reason is appended

#### Scenario: State directory not writable
- **WHEN** the event log cannot be written
- **THEN** the command continues and succeeds as without the log

#### Scenario: No sensitive data
- **WHEN** any event is recorded
- **THEN** it contains no secret values, file paths or user-entered text

### Requirement: Bounded retention
The event log SHALL be capped at 5 MiB by dropping the oldest lines first. Checks that find nothing new SHALL NOT be logged.

#### Scenario: Size cap
- **WHEN** the file exceeds the size cap
- **THEN** the oldest lines are dropped and the newest are kept

#### Scenario: Nothing new
- **WHEN** an update check finds nothing new
- **THEN** no event is written
