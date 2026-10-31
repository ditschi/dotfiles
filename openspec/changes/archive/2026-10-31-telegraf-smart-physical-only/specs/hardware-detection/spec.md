## MODIFIED Requirements

### Requirement: Hardware is detected, not chosen
Ansible SHALL detect on every run whether the host is a laptop (portable chassis with a system battery; batteries of attached devices do not count), a Raspberry Pi and, if so, a Raspberry Pi Zero, and whether it is a virtual machine (a virtualization guest such as KVM, QEMU, VMware, Hyper-V or VirtualBox). These facts SHALL NOT be stored in or read from the host config, and SHALL NOT be detected inside containers.

#### Scenario: Laptop
- **WHEN** Ansible runs on a notebook or convertible with a system battery
- **THEN** the host is detected as a laptop

#### Scenario: Virtual machine
- **WHEN** Ansible runs in a virtual machine without a system battery
- **THEN** the host is detected as a virtual machine and not as a laptop

#### Scenario: Physical host
- **WHEN** Ansible runs directly on hardware, not as a virtualization guest
- **THEN** the host is not detected as a virtual machine

#### Scenario: Desktop with a wireless mouse
- **WHEN** the only battery belongs to a mouse or headset
- **THEN** the host is not detected as a laptop

#### Scenario: Pi Zero
- **WHEN** Ansible runs on a Raspberry Pi Zero, Zero W or Zero 2 W
- **THEN** the host is detected as a Raspberry Pi and as a Pi Zero

### Requirement: Telegraf fragment from the hardware
With the feature `monitoring`, the Telegraf configuration SHALL consist of the base fragment plus the laptop fragment on a laptop, the Pi fragment on a Raspberry Pi, and the server fragment on any other host with the device `server`. The SMART fragment SHALL be added on every host that is neither a virtual machine nor a Raspberry Pi, whatever its device, unless `INFLUX_TELEGRAF_CONFIG_BASE` is set. No other fragment SHALL read SMART data.

#### Scenario: Work laptop is not monitored
- **WHEN** a host has context `work`
- **THEN** no Telegraf configuration is applied, because `monitoring` is excluded for work

#### Scenario: Private laptop
- **WHEN** a private laptop with `monitoring` is applied
- **THEN** Telegraf gets the base, the laptop and the SMART fragment

#### Scenario: Physical server
- **WHEN** a private physical server with `monitoring` is applied
- **THEN** Telegraf gets the base, the server and the SMART fragment

#### Scenario: Virtual server
- **WHEN** a private server with `monitoring` that runs as a virtual machine is applied
- **THEN** Telegraf gets the base and the server fragment, no SMART fragment, and `telegraf` keeps running

#### Scenario: Raspberry Pi
- **WHEN** a Raspberry Pi with `monitoring` is applied
- **THEN** Telegraf gets the base and the Pi fragment and no SMART fragment

#### Scenario: Remote configs
- **WHEN** `INFLUX_TELEGRAF_CONFIG_BASE` is set on a physical host with `monitoring`
- **THEN** the SMART config is not requested from that base and the host reports no SMART data
