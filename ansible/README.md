# Ansible (Dotfiles bootstrap)

OS-Bootstrap for hosts managed by the `machine` CLI. **Not** for K3s/Traefik/Pi-hole stacks — those live in the separate homelab repo (`homelab.yml` is a stub).

## Quick use

```bash
ansible-galaxy collection install -r requirements.yml
# usually via CLI:
machine apply                 # local, uses ~/.local/share/machine/applied-host.yml
machine apply --limit homeserver
```

Host desired state: `../machine/hosts/<hostname>.yml` (context, device, features)  
Feature table: `group_vars/all/features.yml`; every role gate is `'<feature>' in machine_features`, the host's features without the ones the table excludes.  
Hardware facts (`hw_laptop`, `hw_pi`, `hw_pi_zero`): `tasks/detect_hardware.yml`  
Public SSH keys for `ssh_allow_from`: `../machine/ssh_keys/<name>.pub`

## Roles

| Role | Feature / gate |
| --- | --- |
| `monitoring` | `monitoring` |
| `sshd_home` | `sshd-home` — Port 5115 + authorized_keys |
| `stylus_touch_guard` | `stylus-touch-guard` |
| `touch_device` | `touch-device` — GNOME extensions TouchUp + Screen Rotate |
| `lid_switch` | `lid-switch` on detected laptops — closing the lid does nothing |
| `power_profile_switch` | `power-profile-switch` on detected laptops — performance on AC, balanced on battery |
| `battery_charge_limit` | `battery-charge-limit` on detected laptops — 75/80 %, `battery-charge` command |
| `zram_swap` | `zram-swap`, not on Raspberry Pis |
| `thinkpad_l13_yoga_gen2` | detected model, no feature — S3 suspend, tablet OSK ([docs](../docs/thinkpad-l13-yoga-gen2.md)) |

See root [Readme.md](../Readme.md) for architecture, Galaxy decisions, and tests.
