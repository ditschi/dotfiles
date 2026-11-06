# Proposal

## Why

On 2026-11-06 the GNOME session on the laptop ThinkPad-L13-Yoga-Gen-2 (14 GB RAM, Ubuntu, GNOME, systemd 259) repeatedly reported that the Claude desktop app had been stopped for using too much memory, which interrupted the owner's work in Claude. The journals showed the kernel OOM killer (a global OOM), not systemd-oomd: at 00:22 and 00:48 it killed the scope `app-com.anthropic.Claude-*.scope` / `app-gnome-com.anthropic.Claude-*.scope`, and at 00:34 also Syncthing and Bitwarden.

At that time the host had 7.4 GiB zram swap (from the role `zram_swap`: half of RAM, at most 8 GiB) and only a 4 GiB swap file `/swap.img` on disk. zram lives in RAM, so once it is full, RAM is effectively exhausted and the kernel kills the process with the highest OOM score. The Claude app (`oom_score_adj` 100, large RSS, score 743) is usually the one picked. The large consumers were Firefox content processes (about 3.1 GB), the Claude desktop app (about 1.7 GB), a `python3` process (about 1.1 GB) and each Claude Code session (0.3-0.5 GB).

The owner's requirement: the Claude app must not be killed; it may become slower instead.

On 2026-11-06 the owner applied three settings by hand on the L13:

1. `/swap.img` was enlarged from 4 GiB to 16 GiB. zram keeps the higher swap priority (100), the swap file on disk keeps priority -1.
2. `/etc/systemd/system/user@.service.d/90-oomd-limit.conf` sets `ManagedOOMMemoryPressureLimit=80%` in `[Service]`. Ubuntu's default (`/usr/lib/systemd/system/user@.service.d/10-oomd-user-service-defaults.conf`) is `ManagedOOMMemoryPressure=kill` at 50 % for 20 s; the higher limit keeps the additional swapping from making systemd-oomd kill apps instead of the kernel.
3. The user drop-ins `~/.config/systemd/user/app-gnome-com.anthropic.Claude-.scope.d/50-memory-high.conf` and `~/.config/systemd/user/app-com.anthropic.Claude-.scope.d/50-memory-high.conf` set `MemoryHigh=4G` in `[Scope]`. A drop-in directory named after a unit-name prefix ending in a dash applies to every scope of that app, so the kernel reclaims the Claude app's memory into swap first instead of starving other processes.

The goal of this change is to make these three settings reproducible through the dotfiles on the hosts where they fit (ditschi-ThinkPad-T480 and future reinstalls), instead of hand edits.

## What Changes

- A new feature `memory-headroom` with a new local role `memory_headroom` and a new dotfile group `memory-headroom` (names and feature-table values: design.md, Open Questions).
- The role grows the swap file on disk to a target size (16 GiB by default, configurable), never shrinks it, keeps zram at the higher priority, keeps the `/etc/fstab` entry, and skips the resize with a warning when the filesystem would be left with too little free space or the swap file cannot be resized safely.
- The role installs `/etc/systemd/system/user@.service.d/90-oomd-limit.conf` with `ManagedOOMMemoryPressureLimit=80%`, the same file name the owner used on the L13.
- The dotfile group holds the two Claude scope drop-ins with `MemoryHigh=4G`. They are harmless where the Claude desktop app is not installed, because a prefix drop-in that matches no unit has no effect.
- Docs: `docs/features.md`, `docs/thinkpad-l13-yoga-gen2.md` (swap section), the role list in `Readme.md`, a role README.
- Unchanged: the feature `zram-swap`, its role and its sizing.

## Capabilities

### New Capabilities

- `memory-headroom`: disk swap size, the systemd-oomd memory-pressure limit for user sessions, and the memory throttle for the Claude desktop app, on hosts with the feature `memory-headroom`.

### Modified Capabilities

- `feature-selection`: a new requirement for the defaults of the feature `memory-headroom` per context and device (added, so that the existing "Laptop and swap features" list does not grow).
- `system-provisioning`: a new requirement that names `memory_headroom` as a local role (added, so that the enumerated "Local roles" list does not grow).

`hardware-tuning` is not modified: its zram requirement already says that swap on disk stays in place, and this change only sizes that swap.

## Impact

- Ansible: new role `ansible/roles/memory_headroom` (defaults, tasks, handlers, files, README), a play in `ansible/workstation.yml`, a row in `ansible/group_vars/all/features.yml`.
- Dotfiles: new group `home/memory-headroom/.config/systemd/user/` with the two drop-ins.
- Host configs: `machine/hosts/ditschi-ThinkPad-L13-Yoga-Gen-2.yml` and `tests/hosts/ci-home-laptop.yml` list the feature.
- Tests: feature-table tests, a unit test of the swap resize script, a role test without root, the integration test of the CI laptop.
- Profiles: private desktops (L13, T480). Work desktops, servers and containers per the feature-table values in design.md; containers never get it.

## Where the change is made

These planning artifacts are written in the live checkout and pushed to main, because they touch only `openspec/`. The implementation edits `ansible/`, `home/` and the feature table, which `machine` reads from the live checkout, so it is made in the worktree `$(machine repo)/.worktrees/memory-headroom` on branch `memory-headroom`, created from a main that already holds this change directory.
