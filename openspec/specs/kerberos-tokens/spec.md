# kerberos-tokens Specification

## Purpose
Defines how a work machine gets and keeps a Kerberos ticket and finds the password for it.

## Requirements

### Requirement: Password lookup
`get-password [user]` SHALL read the password from the GNOME keyring (`secret-tool`) and SHALL fall back to `$PASSWORD` when the keyring gives none.

#### Scenario: Password in the keyring
- **WHEN** the keyring holds the password
- **THEN** `get-password` prints it

#### Scenario: Keyring not usable
- **WHEN** the keyring gives no password and `$PASSWORD` is set
- **THEN** `get-password` prints the value of `$PASSWORD`

### Requirement: Non-interactive kinit
`kinit-pw` SHALL be a script, not a shell alias, and SHALL run `kinit` without prompting by using `get-password`, so that bash, cron and other non-interactive contexts can use it.

#### Scenario: Use from cron
- **WHEN** cron runs `kinit-pw`
- **THEN** the ticket is requested with the password from `get-password` and no prompt appears

### Requirement: Ticket refresh
`ensure-kerberos-token` SHALL refresh the Kerberos ticket through `kinit-pw` or `kinit` when needed.

#### Scenario: Valid ticket
- **WHEN** the ticket is still valid
- **THEN** it is not refreshed

#### Scenario: Expired ticket
- **WHEN** the ticket is missing or expired
- **THEN** a new ticket is requested

### Requirement: Cron installer
`setup-ensure-kerberos-cron` SHALL install a cron job that runs the refresher.

#### Scenario: Installing the job
- **WHEN** a user runs `setup-ensure-kerberos-cron --install`
- **THEN** a cron job for `ensure-kerberos-token` exists

### Requirement: Refresh at work shell start
On work machines, shell start SHALL run the refresher once. At most once per day it SHALL print a hint when the cron job is missing, so that `crontab -l` does not run on every shell start.

#### Scenario: Missing cron job
- **WHEN** a work shell starts, no hint was shown today and no cron job exists
- **THEN** a hint with the install command is printed

#### Scenario: Hint already shown today
- **WHEN** the hint check ran earlier today
- **THEN** `crontab -l` is not run again
