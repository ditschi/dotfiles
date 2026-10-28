# Spec Delta

## ADDED Requirements

### Requirement: Telegraf installed from the InfluxData source
With the feature `monitoring`, Ansible SHALL add the InfluxData apt source with its signing key and install `telegraf` from it on Debian-family hosts. A failed install SHALL fail the run instead of being skipped silently.

#### Scenario: Ubuntu host with monitoring
- **WHEN** `machine apply` runs on an Ubuntu host with `monitoring` and `telegraf` is not installed
- **THEN** the InfluxData source is added and `telegraf` is installed from it

#### Scenario: Install fails
- **WHEN** the InfluxData source cannot be reached and `telegraf` is not installed
- **THEN** the Ansible run fails and names the Telegraf install

### Requirement: Local Telegraf fragments are the default config
Telegraf SHALL use the local fragments resolved from hardware, device and features as its inputs. When `INFLUX_TELEGRAF_CONFIG_BASE` is set, the service SHALL load the remote configs of those names from that base instead of the local fragments, with the Influx token in its environment. The environment file holding the token SHALL be readable by root only.

#### Scenario: No remote base
- **WHEN** `INFLUX_TELEGRAF_CONFIG_BASE` is empty on a laptop with `monitoring`
- **THEN** Telegraf loads the base and laptop fragments from `/etc/telegraf/telegraf.d`

#### Scenario: Remote base set
- **WHEN** `INFLUX_TELEGRAF_CONFIG_BASE` is set
- **THEN** the Telegraf service starts with one `--config` per resolved name under that base instead of the local fragments and has `INFLUX_TOKEN` in its environment, and the file holding it has mode `0600`

### Requirement: Telegraf output from the Influx credentials
When the Influx credentials are available, Ansible SHALL write the Telegraf output: InfluxDB 2.x when a token is set, otherwise InfluxDB 1.x with user and password. A run without credentials SHALL keep an existing output file unchanged.

#### Scenario: Token available
- **WHEN** `machine apply` runs with the Influx URL and token available
- **THEN** an InfluxDB 2.x output with that URL, token, organisation and bucket is written, readable only by root and the group the Telegraf service runs as

#### Scenario: Credentials missing on a later run
- **WHEN** an output was written earlier and `machine apply` runs without Influx credentials
- **THEN** the existing output is kept and Telegraf keeps shipping metrics

### Requirement: Telegraf runs only with an output
Ansible SHALL enable and start Telegraf when an output is configured and SHALL stop and disable it when none is, so that it does not restart in a loop. A failure to start Telegraf with an output SHALL fail the run.

#### Scenario: Output configured
- **WHEN** `machine apply` finishes on a host with `monitoring` and an output
- **THEN** `telegraf` is enabled and active

#### Scenario: No output
- **WHEN** `machine apply` finishes on a host with `monitoring` and no output
- **THEN** `telegraf` is stopped and disabled and the run prints that the Influx credentials are missing

### Requirement: Telegraf health is reported, not reverted
After an apply on a host with `monitoring`, the health check SHALL report whether Telegraf is not installed, has no output or is not active, and SHALL NOT treat any of these as a failure that restores the previous host config.

#### Scenario: Telegraf not active after apply
- **WHEN** `machine apply` succeeds but `telegraf` is not active
- **THEN** a warning names the reason and the applied host config is kept

### Requirement: Telegraf reports the system hostname
Telegraf SHALL report the host's own system hostname, also when Ansible runs locally against the inventory host `localhost`.

#### Scenario: Local apply
- **WHEN** `machine apply` runs locally on the host `homeserver`
- **THEN** Telegraf's metrics carry the host tag `homeserver`, not `localhost`
