# Spec Delta

## ADDED Requirements

### Requirement: Expected Bitwarden
A host SHALL expect Bitwarden when `BW_SESSION` is set in the environment or in `~/.env.local` and `bw` is installed.

#### Scenario: Saved session
- **WHEN** `~/.env.local` sets `BW_SESSION` and `bw` is installed
- **THEN** the host expects Bitwarden

#### Scenario: No session anywhere
- **WHEN** neither the environment nor `~/.env.local` sets `BW_SESSION`
- **THEN** the host does not expect Bitwarden and nothing about Bitwarden is reported

### Requirement: Expired session is renewed in a terminal
In an interactive run (terminal, without `--yes`), every `machine` step that uses Bitwarden SHALL renew an expected session that `bw` does not accept, without a yes/no question: unlock, or log in and unlock when logged out. Cancelling SHALL let the run continue without Bitwarden.

#### Scenario: Expired session in an interactive update
- **WHEN** a user runs `machine update` in a terminal and the saved session is expired
- **THEN** `bw unlock` asks for the master password at once and the SSH key check and the host list use the new session

#### Scenario: Logged out
- **WHEN** the host expects Bitwarden and `bw` reports it as logged out
- **THEN** the login starts at once with the saved server and the default email

### Requirement: Renewed session replaces the saved one
When the expired session came from `~/.env.local`, the renewed session SHALL replace it there without a question; otherwise the existing opt-in question applies.

#### Scenario: Saved session renewed
- **WHEN** an interactive run renewed a session that `~/.env.local` held
- **THEN** `~/.env.local` holds the new session and nothing was asked about saving it

### Requirement: Expired session needs attention
Without a terminal or with `--yes`, including the background update, a run SHALL check an expected session with `bw status` only, and when it is not unlocked SHALL record an attention item and a prompt segment `⚠ bitwarden: log in (machine)`. `machine attention` SHALL offer to log in now. A run that sees a valid session SHALL clear both.

#### Scenario: Background update with an expired session
- **WHEN** the background update runs and the saved session is no longer accepted
- **THEN** `bw status` is the only `bw` call, `machine attention` lists the Bitwarden item and the prompt shows the segment

#### Scenario: Logged in again
- **WHEN** the user logs in from the attention item or with `machine env pull`
- **THEN** the item and the segment are gone
