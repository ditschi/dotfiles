# Spec Delta

## MODIFIED Requirements

### Requirement: Local event log
The `machine` CLI SHALL append one JSON line per notable event to `events.jsonl` in the machine state directory, only with timestamp, event, outcome, reason code, duration, short revision, context and device. The file SHALL stay on the host and writing SHALL be best effort.

#### Scenario: Automatic update is reverted
- **WHEN** the automatic update reverts after a failed zsh health check
- **THEN** an event with the outcome `reverted` and the reason is appended

#### Scenario: State directory not writable
- **WHEN** the event log cannot be written
- **THEN** the command continues and succeeds as without the log

#### Scenario: No sensitive data
- **WHEN** any event is recorded
- **THEN** it contains no secret values, file paths or user-entered text
