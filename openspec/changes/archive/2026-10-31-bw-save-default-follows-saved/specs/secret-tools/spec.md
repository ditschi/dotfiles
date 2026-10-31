# Spec Delta

## MODIFIED Requirements

### Requirement: Session storage is opt-in
Storing `BW_SESSION` SHALL be opt-in, and SHALL never be done non-interactively. The question SHALL default to no, and to yes when `~/.env.local` already holds a `BW_SESSION`. When a `BW_SESSION` is saved and the user answers no in `machine setup`, it SHALL be removed from `~/.env.local` and the other settings there SHALL be kept.

#### Scenario: Non-interactive run
- **WHEN** `machine env pull` runs without a terminal
- **THEN** `BW_SESSION` is not written to any file

#### Scenario: First save
- **WHEN** a user unlocks Bitwarden in a terminal and `~/.env.local` holds no `BW_SESSION`
- **THEN** the question whether to save the token defaults to no

#### Scenario: Renewal of a saved token in setup
- **WHEN** `~/.env.local` holds an expired `BW_SESSION` and a user renews it in `machine setup`
- **THEN** the question whether to save the token defaults to yes

#### Scenario: Saved token declined
- **WHEN** `~/.env.local` holds a `BW_SESSION` and the user answers no to the save question in `machine setup`
- **THEN** `BW_SESSION` is removed from `~/.env.local` and its CA/proxy settings stay
