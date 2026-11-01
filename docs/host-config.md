# Host config: context, device, hardware and features

What a host is made of, where its choices are stored and how to share them.

Every host has three levels:

| Level | Values | How it is set | Selects |
| --- | --- | --- | --- |
| Context | `private`, `work` | chosen (default: `work` for a company user ID) | dotfile behaviour (Bitwarden group, Git identity, CA bundle, work group, SSH class, `WORK_SETUP`), work roles; private infrastructure only for `private` |
| Device | `desktop` (graphical session), `server` (none), `container` | chosen (default from the boot target); `container` is set in Docker | graphical features |
| Hardware | laptop, Raspberry Pi, Pi Zero | detected by Ansible (`tasks/detect_hardware.yml`) | Pi Zero package set, Telegraf fragment, Docker only where installable |

The feature table [`ansible/group_vars/all/features.yml`](../ansible/group_vars/all/features.yml) lists every feature with its help text, its dotfile groups and, per context and device, `default` (preselected), `optional` or `excluded`; the stricter of the two wins. `machine setup` offers only the features that are not excluded; Ansible applies only those (`machine_features`). A feature in a host config that is excluded or unknown is reported and dropped at the next write.

Adding a feature: one row in the feature table plus either apt packages (`packages_by_feature` in `group_vars/all/packages.yml`), a role with `when: "'<feature>' in machine_features"`, or a dotfile group (`home/<group>/` declared in `mise.toml`, named under `groups:`). The CLI needs no change. Tools for every host go into a `core` fragment instead.

In Docker the device is `container` without context; `MACHINE_CONTEXT_OVERRIDE` and `MACHINE_DEVICE_OVERRIDE` set others (used by `machine testenv` and the tests). `MACHINE_HARDWARE=laptop,pi,pi-zero,vm` replaces the hardware detection in tests (`vm`: a virtual machine, which gets no SMART monitoring).

Work modules (`01_work.zsh`) are only linked for the context `work`.

Fresh setup uses the shell's work-account naming rule
(`^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$`), so `dci2lr` defaults to the context
`work`. Explicit `--context` / `--device` choices and saved host configs take
precedence outside Docker. In Docker (`/.dockerenv` or `MACHINE_IN_DOCKER=1`) the
device is `container` without context, in the CLI and the shell, and `WORK_SETUP`
stays off; set `MACHINE_CONTEXT_OVERRIDE` / `MACHINE_DEVICE_OVERRIDE` to test
another host in a container. The shell exports `MACHINE_CONTEXT` and `MACHINE_DEVICE`.

## Versioning and pushing host configs

```bash
# On the host, once (or after changing features):
machine setup                 # interactive
machine host save             # → machine/hosts/$(hostname -s).yml
machine commit -m "host config" && machine push

# Laptop: allow SSH from this laptop to the server
# edit machine/hosts/homeserver.yml → ssh_allow_from: [this-hostname]
# A new host gets its host config from `machine setup`; to prepare one for
# `machine apply --limit <host>` write machine/hosts/<host>.yml by hand
# (context, device, features, ssh_allow_from), like the files already there.
machine commit -m "allow laptop on homeserver" && machine push

# On the server:
machine update                # pull → sync host config → apply on drift

# Or from the laptop without logging in to the server:
machine apply --limit homeserver
```
