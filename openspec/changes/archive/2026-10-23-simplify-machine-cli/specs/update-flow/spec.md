# Spec Delta

## MODIFIED Requirements

### Requirement: Update never discards local work
`machine update` SHALL first remove text that the local-overrides helper already knows from shared files, then fast-forward without touching local changes. It SHALL stop and report why only when a locally changed file is also changed upstream or the history diverged. Other local changes SHALL be a notice. `--force` overrides a stop.

#### Scenario: Only expected local changes
- **WHEN** the only local changes are blocks that are already stored in a `.local` file
- **THEN** they are removed from the shared file and the update continues

#### Scenario: New local text
- **WHEN** a shared file contains local text that the helper does not know yet and the update does not change that file
- **THEN** the text is left in place and not reported; a manual update may offer the helper

#### Scenario: New local text in a file the update changes
- **WHEN** a shared file with unknown local text is also changed by the incoming commits
- **THEN** the update records a conflict and does not overwrite the text

#### Scenario: Dirty checkout
- **WHEN** a locally changed file is also changed by the incoming commits
- **THEN** the files are listed, the reason is reported and the update stops

#### Scenario: Unrelated local change
- **WHEN** a local change remains that the incoming commits do not touch
- **THEN** the update runs, the local change is kept and reported as a notice

#### Scenario: Diverged history
- **WHEN** a fast-forward is not possible
- **THEN** the update stops and nothing is overwritten
