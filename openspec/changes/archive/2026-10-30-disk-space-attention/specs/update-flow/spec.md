# Spec Delta

## MODIFIED Requirements

### Requirement: Attention entry point
`machine attention`, also run by `machine` without arguments, SHALL list every open item that needs manual action (pending system update, conflicts, diverging values, new local text in a conflicting file, failed update, Telegraf not working on a host with `monitoring`, a filesystem low on space or inodes) and guide the user through each with prompts. Background runs SHALL only record items and SHALL NOT prompt.

#### Scenario: Open items exist
- **WHEN** a user runs `machine attention` and items are open
- **THEN** each item is shown with its choices, and resolved items are removed from the list

#### Scenario: Nothing to do
- **WHEN** no item is open
- **THEN** the command says so and exits successfully

#### Scenario: Non-interactive run
- **WHEN** the command runs without a terminal
- **THEN** it lists the items without prompting

#### Scenario: Blocked update with a conflict
- **WHEN** the update item is open because local changes conflict with the incoming changes
- **THEN** the item offers the conflict choices of an interactive update (see "Conflict choices") and stays open until the conflict is resolved

#### Scenario: System item while the update is blocked
- **WHEN** a system update is pending and the update item is open
- **THEN** the update item is listed first and the system item does not offer `machine apply` on the old checkout; the system step runs as part of the update once it is unblocked

#### Scenario: Stashed local changes
- **WHEN** local changes were put into the stash by `machine` and are not restored yet
- **THEN** an item names the stash entry, shows what it contains and offers to restore it, drop it or keep it for later (default: keep); if restoring conflicts, the files keep the conflict markers, the entry is kept and the commands to finish by hand are shown

#### Scenario: Reverted automatic update
- **WHEN** the update item is open because an automatic update was reverted
- **THEN** the item shows the output of the failed check or step before it offers the update

#### Scenario: Blocked update no longer conflicts
- **WHEN** the update item is open and the local changes now merge cleanly, for example after the user resolved the conflict
- **THEN** the item offers to run the update, which runs the full update including the system step when it is pending

#### Scenario: Telegraf not installed
- **WHEN** the host has `monitoring` and `telegraf` is not installed
- **THEN** a monitoring item says so and offers `machine apply`

#### Scenario: Telegraf without output
- **WHEN** the host has `monitoring`, `telegraf` is installed, no output file exists and the last apply left `telegraf` disabled for lack of an output
- **THEN** a monitoring item names the missing Bitwarden item `influxdb-telegraf-write` and offers `machine apply` once the item exists

#### Scenario: Telegraf not active
- **WHEN** the host has `monitoring`, an output exists and `telegraf` is not active
- **THEN** a monitoring item shows the last lines of the Telegraf journal and offers to restart the service

#### Scenario: Telegraf working
- **WHEN** the host has `monitoring` and `telegraf` is active with an output, or the host does not have `monitoring`
- **THEN** no monitoring item is listed

#### Scenario: Low disk space
- **WHEN** a watched filesystem is low on space or inodes (see the capability `disk-space`)
- **THEN** a disk item names the mount point and its usage and offers the guided cleanup
