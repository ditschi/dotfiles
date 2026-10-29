# Proposal

## Why

A full disk breaks updates, Docker and builds without a clear error, and it is noticed too late. Work hosts have no Telegraf monitoring. The work VM ABTVL421 has a separate data disk at `/mnt/data` that fills up independently of `/`.

## What Changes

- `machine attention` gets a `disk` item for every local filesystem that is low on space or inodes. The check is always on (no feature) and runs live with `statvfs`, so an item disappears as soon as space is freed.
- The filesystems are found automatically from `/proc/self/mountinfo`: types ext4, xfs, btrfs and vfat, read-write only, and each device counted once. A VM with a system disk and a data disk (`/` and `/mnt/data` on ABTVL421) needs no configuration.
- Default threshold: an item when free space is below 5 % **and** below 20 GiB. Inodes count too: an item when free inodes are below 5 %, on filesystems that report inodes.
- An optional host config key `disk_space` sets a different threshold for a mount point (`min_free`, `min_free_percent`) or ignores it (`ignore: true`). Rewriting the host config (`machine setup`, `machine host save`, the applied copy) keeps the key.
- The item shows the known space users on that filesystem (Docker if the host has `docker`, the systemd journal, the apt cache, `~/.cache`, the mise cache). It offers cleanups only after asking. A scan of the biggest directories (`du`) runs only on request.
- The shell prompt shows a disk segment (e.g. `⚠ disk /mnt/data 97%`) next to the update segment. The prompt only reads a state file. A new user timer records the low filesystems every 15 minutes, and so does every `machine` run. `machine status` shows a disk line when a filesystem is low.
- Telegraf disk metrics stay as they are. They are separate from this check and exist only on hosts with `monitoring`.

## Capabilities

### New Capabilities
- `disk-space`: finding the local filesystems, thresholds and their host override, the disk attention item and its cleanups, recording for the prompt, the prompt segment and the status line.

### Modified Capabilities
- `update-flow`: the attention entry point also lists low disk space. This builds on the version of the requirement from `telegraf-runs-reliably`.
- `machine-profiles`: the host config may carry `disk_space`, and every rewrite of the host config keeps it.

Profiles affected: all hosts (work and private, desktop and server). Containers have an overlay root, so they normally get no items. The target case is the work VM ABTVL421 (`/` and `/mnt/data`).

## Impact

- New `machine_cli/disk_space.py` (detection, thresholds, cleanups, state file). `machine_cli/attention.py` (item), `machine_cli/commands.py` (status line, a `machine disk --record` entry point for the timer), `machine_cli/core.py` (`parse_profile_text`, `format_profile_yaml`, `profile_fingerprint` carry `disk_space`), `machine_cli/profile.py`.
- Shell: `home/core/.zsh/update-state.sh` (disk segment), `home/core/.zsh/config/03_theme.zsh`, `home/core/.bashrc`, `home/prompt/.config/starship.toml`.
- New user units `home/systemd/.config/systemd/user/machine-disk-check.{service,timer}`, enabled the way `dotfiles-update-check.timer` is enabled (`machine_cli/updates.py`).
- `machine/hosts/README.md` (document `disk_space`), `Readme.md`.
- Tests in `tests/unit/` (detection from a fake mountinfo, thresholds, override, host config round trip, segment).
- Order: implemented after `telegraf-runs-reliably` is archived, because both edit `machine_cli/attention.py` and the `Attention entry point` requirement.
