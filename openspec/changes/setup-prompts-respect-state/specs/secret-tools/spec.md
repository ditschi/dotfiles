# Spec Delta

## ADDED Requirements

### Requirement: A valid saved session suppresses Bitwarden prompts
`machine setup` SHALL read `~/.env.local` before it asks anything about Bitwarden, and SHALL NOT ask to configure, log in or unlock when the saved `BW_SESSION` is accepted by `bw`.

#### Scenario: Saved session is valid
- **WHEN** `~/.env.local` holds a `BW_SESSION` that `bw status` reports as unlocked and a user runs `machine setup`
- **THEN** no Bitwarden question is asked
