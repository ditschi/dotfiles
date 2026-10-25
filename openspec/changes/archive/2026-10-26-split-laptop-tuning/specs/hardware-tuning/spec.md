# Spec Delta

## Purpose

Defines what the hardware-related system features do (lid, power profile, battery charge limit, zram swap), on which detected hardware Ansible applies them, and how tuning for one hardware model is selected by the hardware itself instead of by a feature.

## ADDED Requirements

### Requirement: Closing the lid does nothing
With the feature `lid-switch` on a detected laptop, closing the lid SHALL trigger no action from the system, on battery, on the charger and when docked. The setting SHALL be kept in its own configuration file, so that a system package update does not reset it.

#### Scenario: Lid closed on battery
- **WHEN** a laptop with `lid-switch` runs on battery and the lid is closed
- **THEN** the host does not suspend, hibernate or shut down

#### Scenario: Lid closed on the charger
- **WHEN** a laptop with `lid-switch` is on the charger and the lid is closed
- **THEN** the host does not suspend, hibernate or shut down

#### Scenario: System package update
- **WHEN** the package that ships the default login manager configuration is updated
- **THEN** closing the lid still does nothing

### Requirement: Power profile follows the power source
With the feature `power-profile-switch` on a detected laptop, the power profile SHALL be `performance` while the charger is plugged in and `balanced` on battery, set at boot and each time the charger is plugged in or out. Both profiles SHALL be configurable per host. A profile picked by hand SHALL stay until the next plug event or boot. A profile the host does not offer SHALL leave the profile unchanged and be reported, without failing the boot or the Ansible run.

#### Scenario: Charger plugged in
- **WHEN** the charger of a laptop with `power-profile-switch` is plugged in
- **THEN** the power profile becomes `performance`

#### Scenario: Charger unplugged
- **WHEN** the charger is unplugged
- **THEN** the power profile becomes `balanced`

#### Scenario: Profile not offered
- **WHEN** the host does not offer the profile `performance`
- **THEN** the profile stays unchanged and no unit fails

### Requirement: Battery charge limit
With the feature `battery-charge-limit` on a detected laptop, every battery that offers charge thresholds through the kernel SHALL start charging below 75 % and stop at 80 %, applied at boot. Both values SHALL be configurable per host. A battery that offers only a stop threshold SHALL get the stop threshold; a host without such a battery SHALL be left unchanged without error.

#### Scenario: Laptop with start and stop threshold
- **WHEN** a laptop with `battery-charge-limit` boots
- **THEN** each of its batteries charges between 75 % and 80 %

#### Scenario: Battery with only a stop threshold
- **WHEN** a battery offers only a stop threshold
- **THEN** charging stops at 80 % and no error is reported

#### Scenario: Host with two batteries
- **WHEN** a laptop has two batteries with charge thresholds
- **THEN** both get the thresholds

### Requirement: Charging to full on request
A command SHALL show each battery's level and thresholds, switch to charging to full (for example before a trip), and switch back to the normal thresholds. The next boot SHALL restore the normal thresholds.

#### Scenario: Before a trip
- **WHEN** the user runs the command to charge to full
- **THEN** the batteries charge to 100 % until the user switches back or the host reboots

### Requirement: Laptop features only on laptops
`lid-switch`, `power-profile-switch` and `battery-charge-limit` SHALL be applied only when Ansible detects a laptop. On other hardware they SHALL stay selected without effect.

#### Scenario: Work VM with the work defaults
- **WHEN** the work VM has the laptop features from the work desktop defaults and `machine apply` runs
- **THEN** none of the three is applied and the run does not fail

### Requirement: zram swap
With the feature `zram-swap`, the host SHALL have compressed swap in RAM, sized from the RAM (half of it, at most 8 GiB, configurable) and used before any swap on disk. Swap on disk SHALL stay in place. On a detected Raspberry Pi it SHALL NOT be applied.

#### Scenario: Memory pressure
- **WHEN** a host with `zram-swap` runs low on memory
- **THEN** pages are swapped to the compressed RAM swap before the swap file on disk

#### Scenario: Host with more RAM
- **WHEN** the host has 32 GiB RAM
- **THEN** the compressed swap is at most 8 GiB

#### Scenario: Raspberry Pi
- **WHEN** a Raspberry Pi has `zram-swap` selected
- **THEN** no zram swap is configured

### Requirement: Model tuning selected by the hardware
Tuning for one hardware model SHALL be applied when the hardware reports that model, without a feature. It SHALL NOT be offered in the feature menu and SHALL NOT be applied on other hardware or in containers.

#### Scenario: ThinkPad L13 Yoga Gen 2
- **WHEN** Ansible runs on a host whose hardware reports vendor LENOVO and model `ThinkPad L13 Yoga Gen 2`
- **THEN** its model tuning is applied: S3 as the default suspend mode, with a warning when the firmware does not offer it, and the on-screen keyboard in tablet mode

#### Scenario: Other ThinkPad
- **WHEN** Ansible runs on another ThinkPad model
- **THEN** the L13 Yoga Gen 2 tuning is not applied

#### Scenario: Feature menu
- **WHEN** `machine setup` shows the feature menu on any host
- **THEN** no model tuning is listed
