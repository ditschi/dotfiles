# Spec Delta

## MODIFIED Requirements

### Requirement: Model tuning selected by the hardware
Tuning for one hardware model SHALL be applied when the hardware reports that model, without a feature. It SHALL NOT be offered in the feature menu and SHALL NOT be applied on other hardware or in containers.

#### Scenario: ThinkPad L13 Yoga Gen 2
- **WHEN** Ansible runs on a host whose hardware reports vendor LENOVO and model `ThinkPad L13 Yoga Gen 2`
- **THEN** its model tuning is applied: S3 as the default suspend mode, with a warning when the firmware does not offer it, the command `touchpad-reset`, and the on-screen keyboard in tablet mode

#### Scenario: Other ThinkPad
- **WHEN** Ansible runs on another ThinkPad model
- **THEN** the L13 Yoga Gen 2 tuning is not applied

#### Scenario: Feature menu
- **WHEN** `machine setup` shows the feature menu on any host
- **THEN** no model tuning is listed

#### Scenario: Touchpad and TrackPoint frozen
- **WHEN** touchpad and TrackPoint of the L13 Yoga Gen 2 stop responding and the user runs `touchpad-reset`
- **THEN** the `elan_i2c` driver is reloaded, asking for sudo when needed, and both work again
