# Spec Delta

## ADDED Requirements

### Requirement: Interactive selection by checklist
In a terminal, the selection of features SHALL be a checklist: the arrow keys move, space toggles the entry under the cursor, Enter confirms, and the preselected features are ticked. Where the terminal cannot deliver key presses, the selection SHALL fall back to a prompt where numbers toggle entries relative to the preselection.

#### Scenario: Selecting with the keyboard
- **WHEN** a user runs `machine setup` in a terminal and presses down, space and Enter on a preselected feature list
- **THEN** the second feature's tick is flipped and the others keep their preselection

#### Scenario: Keys cannot be read
- **WHEN** key presses cannot be read from the terminal
- **THEN** the user toggles features by number, Enter keeping the preselection
