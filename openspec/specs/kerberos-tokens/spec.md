# kerberos-tokens Specification

## Purpose
Defines how a work machine gets and keeps a Kerberos ticket and finds the password for it.

## Requirements

### Requirement: Password lookup
`get-password [user]` SHALL print the owner's password from the env files (`$PASSWORD`, or `PASSWORD` read from `~/.env`, `~/.env.host` and `~/.env.local` with the shell loader's rules when it is not in the environment). Only when no env password exists SHALL it read the GNOME keyring (`secret-tool`). It SHALL NOT prompt, open an unlock dialog or block on a locked keyring.

#### Scenario: Password in the env files
- **WHEN** `PASSWORD` is set in `~/.env` and the keyring holds a different password
- **THEN** `get-password` prints the value from the env files

#### Scenario: Called from a service
- **WHEN** a systemd user service without the shell environment calls `get-password` and `~/.env` sets `PASSWORD`
- **THEN** `get-password` prints that value

#### Scenario: Password in the keyring
- **WHEN** no env password exists and the keyring is unlocked and holds the password
- **THEN** `get-password` prints the keyring password

#### Scenario: Keyring not usable
- **WHEN** the keyring gives no password and `$PASSWORD` is set
- **THEN** `get-password` prints the value of `$PASSWORD`

#### Scenario: Locked keyring
- **WHEN** no env password exists and the keyring is locked
- **THEN** `get-password` exits non-zero within a few seconds and no unlock dialog appears

### Requirement: Non-interactive kinit
`kinit-pw` SHALL be a script, not a shell alias, and SHALL run `kinit` without prompting by using `get-password`, so that bash, systemd user services and other non-interactive contexts can use it.

#### Scenario: Use from cron
- **WHEN** a non-interactive job, such as cron or a systemd user service, runs `kinit-pw`
- **THEN** the ticket is requested with the password from `get-password` and no prompt appears

### Requirement: Ticket refresh
`ensure-kerberos-token` SHALL keep the Kerberos ticket valid. When the ticket expires within 2 hours and can still be renewed, it SHALL renew it without a password. When the ticket is missing, expired or no longer renewable, it SHALL request a new one through `kinit-pw`, but only when the KDC is reachable and the failure guard allows it.

#### Scenario: Valid ticket
- **WHEN** the ticket is valid for more than 2 hours
- **THEN** it is neither renewed nor requested again

#### Scenario: Ticket close to expiry
- **WHEN** the ticket expires within 2 hours and its renewal limit has not passed
- **THEN** it is renewed without using the password

#### Scenario: Expired ticket
- **WHEN** the ticket is missing or expired and the KDC is reachable
- **THEN** a new ticket is requested

#### Scenario: KDC not reachable
- **WHEN** the ticket is missing and the KDC is not reachable
- **THEN** no request is made and no failure is counted

### Requirement: Keyring follows the env password
When an env password exists and the GNOME keyring is unlocked, the keyring entry that `get-password` reads SHALL be updated to the env password if it differs. A locked keyring SHALL be left unchanged and SHALL NOT be prompted for.

#### Scenario: Stale keyring entry
- **WHEN** the env password was changed, the keyring is unlocked and still holds the old password
- **THEN** the keyring entry is replaced by the env password

#### Scenario: Keyring locked
- **WHEN** the keyring is locked
- **THEN** the keyring is not changed and no dialog appears

### Requirement: Ticket refresh by a user timer
On hosts with the `kerberos` feature, a systemd user timer SHALL run the ticket refresh at boot and at least every 10 minutes, also when the owner is not logged in. The refresh SHALL also run when the VPN watcher finds the work network reachable.

#### Scenario: Remote VM without login
- **WHEN** nobody is logged in to the VM and the ticket expires within 2 hours
- **THEN** the timer renews it

#### Scenario: Host without the feature
- **WHEN** a host does not have the `kerberos` feature
- **THEN** no Kerberos timer is enabled

### Requirement: Authentication failure guard
Automatic `kinit` and VPN attempts SHALL share one failure guard. Only a rejected password SHALL count as a failure; network errors SHALL NOT. After 2 counted failures at least 15 minutes apart, or at once when the account is locked or the password has expired, automatic attempts SHALL stop and a desktop notification SHALL name the reason.

#### Scenario: Network error
- **WHEN** `kinit` fails because no KDC can be contacted
- **THEN** no failure is counted

#### Scenario: Stale password
- **WHEN** two automatic attempts at least 15 minutes apart are rejected with an incorrect password
- **THEN** no further automatic `kinit` or VPN attempt is made and the owner is notified

#### Scenario: Account locked
- **WHEN** the KDC reports that the account's credentials have been revoked
- **THEN** automatic attempts stop immediately and the owner is notified

#### Scenario: Second failure too early
- **WHEN** one failure was counted less than 15 minutes ago
- **THEN** no automatic attempt is made before 15 minutes have passed

### Requirement: Guard reset
The failure guard SHALL be reset when the owner runs `kinit-pw` or `vpn-pw` in a terminal, and when the password that `get-password` returns differs from the one that was last rejected. A manual run that fails SHALL count as a failure again.

#### Scenario: Manual run after a fix
- **WHEN** the guard has stopped and the owner runs `kinit-pw` in a terminal
- **THEN** the guard is reset before the attempt and automatic attempts resume when it succeeds

#### Scenario: Password updated
- **WHEN** the guard has stopped and the env password changes
- **THEN** the guard is reset and the next automatic attempt uses the new password

#### Scenario: Manual run still fails
- **WHEN** the owner runs `kinit-pw` in a terminal and the password is rejected again
- **THEN** the failure is counted and automatic attempts stop again after the limit

### Requirement: Ticket status at work shell start
On work machines, shell start SHALL NOT request or renew a Kerberos ticket. It MAY show whether a valid ticket exists, using only a local check.

#### Scenario: Shell start without ticket
- **WHEN** a work shell starts and no valid ticket exists
- **THEN** no `kinit` runs and the shell starts without contacting the KDC

### Requirement: Bounded Kerberos calls
Automatic `kinit` and `kinit -R` SHALL be stopped after 30 seconds and the KDC check after 2 seconds. A stopped call SHALL be logged, SHALL NOT count as a failure for the guard, and SHALL be retried on the next run.

#### Scenario: Hanging kinit
- **WHEN** an automatic `kinit` does not finish within 30 seconds
- **THEN** it is stopped, the timeout is logged, no failure is counted and the next timer run tries again

### Requirement: Status view
`work-net status` SHALL show, without changing anything: the ticket's expiry and renewal limit, whether the KDC is reachable, the guard state with its reason, and the last automatic action with its time and outcome. It SHALL NOT print the password.

#### Scenario: Guard stopped
- **WHEN** the guard stopped after two rejected passwords and the owner runs `work-net status`
- **THEN** the output names the stop, its reason and how to reset it
