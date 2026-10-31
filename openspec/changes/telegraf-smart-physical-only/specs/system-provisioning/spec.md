## ADDED Requirements

### Requirement: Telegraf can read SMART data
On a host whose Telegraf configuration includes the SMART fragment, Ansible SHALL install `smartmontools` and SHALL allow the `telegraf` user to run `smartctl`, and only `smartctl`, as root without a password. The rule SHALL be validated before it is put in place, so that an invalid rule never breaks `sudo`. On a host with `monitoring` but without the SMART fragment, Ansible SHALL remove that rule and SHALL NOT install `smartmontools` for Telegraf.

#### Scenario: Physical host with monitoring
- **WHEN** `machine apply` runs on a physical private host with `monitoring`
- **THEN** `smartmontools` is installed, `telegraf` may run `smartctl` through `sudo` without a password, and `telegraf` is active with the SMART input

#### Scenario: Nothing else allowed
- **WHEN** the `telegraf` user runs any command other than `smartctl` through `sudo`
- **THEN** `sudo` refuses it

#### Scenario: Virtual machine
- **WHEN** `machine apply` runs on a virtual machine with `monitoring`
- **THEN** no `smartctl` rule for `telegraf` exists and `smartmontools` is not installed for Telegraf

#### Scenario: Host leaves the SMART fragment
- **WHEN** a host with `monitoring` that had the SMART fragment no longer resolves it (for example after `INFLUX_TELEGRAF_CONFIG_BASE` is set) and `machine apply` runs
- **THEN** the `smartctl` rule for `telegraf` is removed; an installed `smartmontools` package is kept
