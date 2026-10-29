# Design

## Context

See proposal.md (Why). Relevant current state:

- `machine attention` builds its list from `AttentionItem`s in `machine_cli/attention.py`. Each item has a text, an optional yes/no question and a `resolve` callable. `telegraf-runs-reliably` adds a `monitoring` item there.
- The shell prompt reads `~/.dotfiles-update-state` with builtins only (`home/core/.zsh/update-state.sh`), exports `DOTFILES_UPDATE_SEGMENT` and shows it through Starship (`env_var`), the zsh `RPROMPT` fallback and the bash `PS1`. The prompt must not start a process.
- The only background job is `dotfiles-update-check.timer` (every 6 h), which runs `machine update --auto`.
- The host config is parsed by `parse_profile_text` and written by `format_profile_yaml` in `machine_cli/core.py`. Both know only `context`, `device`, `features`, `ssh_allow_from` and `ansible`. A rewrite drops every other key today. `profile_fingerprint` decides whether the repository file differs from the applied copy.
- Telegraf already collects `inputs.disk` on hosts with `monitoring`. Work hosts exclude `monitoring`.
- ABTVL421 (work VM, desktop, `docker`) has its system disk at `/` and a data disk at `/mnt/data`.

## Goals / Non-Goals

**Goals:**
- One live check, used by `machine attention`, `machine status` and the recorder for the prompt.
- Correct handling of hosts with several disks without configuration.

**Non-Goals:**
- Alerting outside the host (that is Telegraf/Influx on monitoring hosts).
- Automatic cleanup. Nothing is deleted without the user picking it.
- History or trends of disk usage.

## Decisions

### Always on, no feature
The check runs on every host. A feature flag would only hide it, and an item appears only when a filesystem is actually low. The owner decided this.

### Filesystems found from mountinfo, fixed type list
Watched: read-write ext4, xfs, btrfs and vfat from `/proc/self/mountinfo`, each device (major:minor) once under its shortest mount point. The owner confirmed this type list as the default. This covers a VM with a system disk and a data disk (ABTVL421: `/` and `/mnt/data`), separate `/boot` and `/boot/efi`, and a separate Docker disk. tmpfs, overlay, squashfs/snap and network filesystems are left out. That keeps containers and snaps silent and avoids hanging on an unreachable network mount.

Alternative considered: a list of mount points per host only. It was not chosen because the owner wants it to work without configuration. An explicit list stays possible through the host config key.

### Threshold: below 5 % and below 20 GiB free
The owner chose this default over three alternatives: below 10 % and below 50 GiB, below 10 % only (a 2 TB disk would warn at 200 GB free), and the other combinations offered. Both conditions must hold, so large disks are judged by the absolute amount and small partitions (`/boot`) by the percentage. "Free" is the space available to the user (`f_bavail`), not including the root reserve, because that is what fails for the user. Inodes use the same 5 % on filesystems that report inode counts (`f_files > 0`). vfat and btrfs report none.

### Optional `disk_space` host config key
The owner wants an optional per-host key in addition to the defaults. It is a list of `{path, min_free, min_free_percent, ignore}` entries in `machine/hosts/<host>.yml`. The check reads it from the applied host config, which is what the shell reads too and which also exists on hosts without a repository file. `parse_profile_text`, `format_profile_yaml` and `profile_fingerprint` carry the key through unchanged, so `machine setup` and `machine host save` no longer drop it and a change is taken over by `machine update`.

### Prompt segment from a state file, refreshed by a 15-minute timer
The owner wants the prompt to show low disk space. The prompt cannot call `statvfs` without starting a process, so `machine` writes a state file (`~/.local/share/machine/disk-state`, `key=value` lines like the update state, with the ready-made segment text) and the shell reads it with builtins. A new user timer `machine-disk-check.timer` runs `machine disk --record` every 15 minutes, and every `machine` command records it at the end too. That includes `machine attention` after a cleanup, so the segment goes away right after the user freed space.

The owner chose the 15-minute timer over two alternatives: recording only with the 6 h update check, where the warning could lag up to 6 h, and an hourly timer. The timer is installed with the `systemd` dotfile group and enabled the same way as `dotfiles-update-check.timer`.

### Order after `telegraf-runs-reliably`
The owner decided to implement this change after `telegraf-runs-reliably` is archived. Both edit `machine_cli/attention.py` and the requirement "Attention entry point". The `update-flow` delta here is written on top of the version from that change.

### Override semantics, no startup line, cleanups
The owner confirmed three further points:

- Thresholds in a `disk_space` entry replace both default space thresholds. With only `min_free: 100G` the filesystem is low below 100 GiB, whatever the percentage. With both given, it must be below both. The rejected alternative was to replace only the threshold that is named and keep the default 5 % for the other.
- Low disk space prints no line at shell start. Only the prompt segment and `machine status` show it, so the shell start stays quiet. The rejected alternative was a one-line message like the one for a failed update.
- The item offers `sudo apt-get clean`, `sudo journalctl --vacuum-size=200M`, `docker system prune` (Docker asks itself) and `mise cache clear`. `~/.cache` is only shown with its size and is never cleaned as a whole. The rejected alternative was to also offer emptying `~/.cache`.

## Assumptions

Not confirmed by the owner. Change them before implementation if they are wrong.

- The disk segment is a separate variable (`DOTFILES_DISK_SEGMENT`) next to the update segment, not merged into it. The update segment keeps its meaning, and both can show at once.
- A mount point named in `disk_space` is watched even when its type is not in the default list.
- The directory scan is `du -xh -d 2 <mount>`, sorted, the 20 largest, with `sudo` when the user is not root.
- Sizes of the known space users are measured only when the item is opened in a terminal, and only for locations on the same device as the low filesystem.
- The recorder does not write to the event log (`events.jsonl`), because nothing is done automatically.

## Risks / Trade-offs

- [Prompt shows a stale state for up to 15 minutes] → Every `machine` run records the state too. `machine attention` always computes live.
- [Measuring `~/.cache` or the journal is slow on large trees] → Measured only on opening the item in a terminal, and only for locations on the low filesystem. The full directory scan runs only on request.
- [A host config rewrite elsewhere still drops `disk_space`] → Round-trip unit test for every writer (`format_profile_yaml`, takeover, `machine host save`).
- [A data disk that is meant to run full nags forever] → `ignore: true` or a lower threshold in `disk_space`.
- [`/proc/self/mountinfo` inside a container shows host mounts through bind mounts] → Only the listed types and only read-write mounts count. A container that bind-mounts a host disk does see it, which is correct for the user of that container.

## Migration Plan

No migration. On the next `machine update` the new units are linked and the timer is enabled. Hosts without the key get the defaults. Rollback: revert the change. The state file is then just ignored, and `systemctl --user disable --now machine-disk-check.timer` stops the timer.
