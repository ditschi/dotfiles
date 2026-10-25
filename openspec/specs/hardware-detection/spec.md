# hardware-detection Specification

## Purpose
Defines which hardware facts Ansible detects on a host and what follows from them, so that hardware-dependent settings need no choice in the host config.

## Requirements

### Requirement: Hardware is detected, not chosen
Ansible SHALL detect on every run whether the host is a laptop (portable chassis with a system battery; batteries of attached devices do not count), a Raspberry Pi and, if so, a Raspberry Pi Zero. These facts SHALL NOT be stored in or read from the host config, and SHALL NOT be detected inside containers.

#### Scenario: Laptop
- **WHEN** Ansible runs on a notebook or convertible with a system battery
- **THEN** the host is detected as a laptop

#### Scenario: Virtual machine
- **WHEN** Ansible runs in a virtual machine without a system battery
- **THEN** the host is not detected as a laptop

#### Scenario: Desktop with a wireless mouse
- **WHEN** the only battery belongs to a mouse or headset
- **THEN** the host is not detected as a laptop

#### Scenario: Pi Zero
- **WHEN** Ansible runs on a Raspberry Pi Zero, Zero W or Zero 2 W
- **THEN** the host is detected as a Raspberry Pi and as a Pi Zero

### Requirement: Pi Zero package set
A Pi Zero SHALL get the slim base package set instead of the full one.

#### Scenario: Packages on a Pi Zero
- **WHEN** Ansible resolves the packages on a Pi Zero
- **THEN** the slim base set is used and the host package set is not added

### Requirement: Docker only where installable
With the feature `docker`, Ansible SHALL install Docker only when the package is available for the host's architecture, and SHALL otherwise report that it was skipped without failing.

#### Scenario: Original Pi Zero
- **WHEN** a host with `docker` is a Pi Zero with an ARMv6 CPU and no Docker package is available
- **THEN** Docker is not installed, the run reports it and does not fail

#### Scenario: Pi Zero 2 W
- **WHEN** the Docker package is available for the architecture
- **THEN** Docker is installed

### Requirement: Telegraf fragment from the hardware
With the feature `monitoring`, the Telegraf configuration SHALL consist of the base fragment plus the laptop fragment on a laptop, the Pi fragment on a Raspberry Pi, and the server fragment on any other host with the device `server`.

#### Scenario: Work laptop is not monitored
- **WHEN** a host has context `work`
- **THEN** no Telegraf configuration is applied, because `monitoring` is excluded for work

#### Scenario: Private laptop
- **WHEN** a private laptop with `monitoring` is applied
- **THEN** Telegraf gets the base and the laptop fragment
