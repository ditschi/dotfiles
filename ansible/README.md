# Ansible (Dotfiles bootstrap)

OS-Bootstrap for hosts managed by the `machine` CLI. **Not** for K3s/Traefik/Pi-hole stacks — those live in the separate homelab repo (`homelab.yml` is a stub).

## Quick use

```bash
ansible-galaxy collection install -r requirements.yml
# usually via CLI:
machine apply                 # local, uses ~/.config/machine/profile.yml
machine apply --limit homeserver
```

Host desired state: `../machine/hosts/<hostname>.yml`  
Public SSH keys for `ssh_allow_from`: `../machine/ssh_keys/<name>.pub`

## Roles

| Role | Feature / gate |
| --- | --- |
| `user_tools` | non-container profiles |
| `monitoring` | `monitoring` |
| `sshd_home` | `sshd-home` — Port 5115 + authorized_keys |
| `stylus_touch_guard` | `stylus-touch-guard` |

See root [Readme.md](../Readme.md) for architecture, Galaxy decisions, and tests.
