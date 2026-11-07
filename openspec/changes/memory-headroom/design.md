# Design

## Context

See proposal.md for the incident and the three settings the owner applied by hand on ThinkPad-L13-Yoga-Gen-2, and specs/memory-headroom/spec.md for the required behaviour.

Relevant repository structure:

- The feature table `ansible/group_vars/all/features.yml` is the single source for feature help, dotfile groups and defaults per context (private, work) and device (desktop, server, container). Ansible conditions use `machine_features`, which already drops features the table excludes for the host (spec `feature-selection`).
- The role `zram_swap` (feature `zram-swap`, preselected on desktops and servers, excluded in containers, not applied on a detected Raspberry Pi) writes `/etc/systemd/zram-generator.conf` (`zram-size = min(ram / 2, 8192)`, `swap-priority = 100`) and `/etc/sysctl.d/99-zram.conf` (`vm.swappiness = 100`, `vm.page-cluster = 0`). It does not touch swap on disk; spec `hardware-tuning` requires that swap on disk stays in place.
- Hardware facts come from `ansible/tasks/detect_hardware.yml` (`hw_laptop`, `hw_pi`, `hw_virtual`, ...); in containers all are false. `machine_manage_services` is false in containers and CI, where roles install files but do not start services.
- Dotfile groups under `home/<group>/` are symlinked into `$HOME`. A host gets `systemd` unless it is a container, plus the groups its features name (`groups:` in the feature table). The step `update timers` (`ensure_update_timer` in `machine_cli/updates.py`) runs `systemctl --user daemon-reload` after `machine setup`, `machine apply` and `machine update` whenever the group `systemd` is present.
- The Claude desktop app is not installed by the dotfiles; the feature `claude-code` installs only the CLI. There is no feature for the desktop app.
- Role tests run the role on localhost against paths under `tmp_path` without root (`tests/unit/test_monitoring_role.py`); helper scripts are tested against fake paths and stub commands (`tests/unit/test_laptop_scripts.py`). The integration test `tests/integration/test_host_yaml_install.py` applies the CI laptop host `tests/hosts/ci-home-laptop.yml` in a Docker container. There is no molecule setup.

systemd and kernel behaviour this design relies on (man pages of systemd 255 on homeserver; the L13 runs 259, see Assumptions):

- `MemoryHigh=` throttles a unit above the limit and makes the kernel reclaim its memory first; it never kills. It is a resource-control setting and works for scope units, also through drop-ins of transient units.
- A drop-in directory `<prefix>-.scope.d/` applies to every scope whose name starts with `<prefix>-`; a drop-in for a unit that never exists has no effect.
- `ManagedOOMMemoryPressure=kill` on `user@.service` makes systemd-oomd kill a descendant cgroup when the memory pressure of the user manager stays above `ManagedOOMMemoryPressureLimit=` for the configured duration (Ubuntu default: 50 % for 20 s).
- `ManagedOOMSwap=kill` on `-.slice` makes systemd-oomd kill the cgroup with the most swap when memory and swap use both exceed `SwapUsedLimit=` (default 90 %). On homeserver (Ubuntu, systemd 255) the shipped drop-in sets `ManagedOOMSwap=auto`, which disables this; the L13 has the same value (see Verified on the L13).
- `ManagedOOMPreference=avoid|omit`: for swap-based kills, systemd-oomd respects it only on cgroups owned by root; for memory-pressure kills, it also respects it when the cgroup and the monitored ancestor have the same owner (`systemd.resource-control(5)`, systemd 255). A Claude scope under `user@1000.service` monitored for memory pressure on `user@1000.service` therefore may honour it; a swap-based kill decided on `-.slice` ignores it.
- The kernel OOM killer picks by OOM score (memory use plus `oom_score_adj`); `MemoryHigh` and `MemoryLow` do not exempt a process from it. An unprivileged process can raise `oom_score_adj`, but lowering it below the minimum set by a privileged process needs `CAP_SYS_RESOURCE`.

## Goals / Non-Goals

**Goals:**
- On hosts with the feature, the three settings from the L13 are applied by `machine setup`, `machine apply` and `machine update --system` and need no hand edits.
- The Claude desktop app is slowed down under memory pressure rather than killed.
- Hosts without the Claude desktop app, containers, Raspberry Pis and hosts with little free disk space are not harmed.

**Non-Goals:**
- Installing or updating the Claude desktop app.
- Changing the zram size or the feature `zram-swap`.
- Limiting Firefox, `python3` processes or Claude Code sessions (decision 10).
- Hibernation (needs swap of at least the RAM size and other configuration; S3 made it unnecessary on the L13).

## Decisions

1. **The three settings are reproduced as the owner applied them on the L13.** Swap file on disk at 16 GiB with priority below zram, `ManagedOOMMemoryPressureLimit=80%` for `user@.service`, and `MemoryHigh` for every scope of the Claude desktop app (applied as 4G, raised to 8G by decision 4), both under the GNOME launcher name (`app-gnome-com.anthropic.Claude-`) and the plain one (`app-com.anthropic.Claude-`).
2. **The Claude app is slowed down, never killed by the dotfiles' own settings.** Nothing in this change kills, stops or restarts the app; every setting either adds room (swap) or throttles (`MemoryHigh`).
3. **Containers never get it.** A container sees the host's memory and swap and has no own systemd user manager to configure.

4. **`MemoryHigh=8G` for both Claude scopes (owner decision, 2026-11-06).** Measured on the L13 the same day: the scope `app-gnome-com.anthropic.Claude-*` holds only the Electron UI (1.0 GB now, peak 1.8 GB); the scope `app-com.anthropic.Claude-*` holds every Claude Code session and everything it starts (shells, ssh, python3, tests, builds), with a peak of 6.2 GB before any limit (the python3 process the kernel killed at 00:48 ran there). `MemoryHigh` throttles as soon as the scope exceeds it, even with free RAM, so 4G would slow normal agent work. With the 16 GiB swap file and the oomd limit at 80 % in place, the limit is only a brake against a runaway scope; 8G (a little over half of 14 GB RAM) is above the measured peak and still leaves room for the rest of the session. One value for both drop-ins keeps the group simple; the UI scope never reaches it. `MemoryLow=` protection for Claude was considered and rejected: without root it is ineffective, because the ancestors `user.slice` and `user@.service` have no `memory.low`.

5. **`OOMPolicy=continue` in both Claude drop-ins (owner decision, 2026-11-07).** Task 1.1 found that systemd ended the whole Claude scope after every kernel OOM kill of a single process in it (`OOMPolicy=stop`), also when the victim was only a `python3` child of a Claude Code session. With `continue`, the kernel kill hits only the victim and the app keeps running, which is the owner's requirement.
6. **`MemoryHigh=8G` stays a fixed value (owner decision, 2026-11-07).** No percentage of RAM and no lower value for smaller hosts until such a host gets the feature (former Open Question 2).
7. **Swap file: a fixed 16 GiB, grow only, with a free-space guard (owner decision, 2026-11-07).** Variable `memory_headroom_swapfile_size_gib` (default 16); the file is not grown when less than 20 GiB and 5 % of the filesystem would remain free. 16 GiB is the size proven on the L13 (former Open Question 1).
8. **systemd-oomd stays on for user sessions with the limit at 80 % (owner decision, 2026-11-07).** It stays the safety net for a runaway process while the larger swap file is used (former Open Question 4).
9. **Swap-based systemd-oomd kills are switched off by the role (owner decision, 2026-11-07).** The role installs `/etc/systemd/system/-.slice.d/90-oomd-no-swap-kill.conf` with `ManagedOOMSwap=auto`. Ubuntu ships the same value today, so the file changes nothing on current hosts; it keeps it that way if a distribution default turns it on, because `MemoryHigh` makes the Claude app the largest swap user and a swap-based kill ends a whole cgroup (the whole app), while a kernel kill with decision 5 ends one process. Accepted trade-off: a later deliberate distribution change to `kill` is overridden on hosts with the feature (former Open Question 8).
10. **No further protection and no other limits in this change (owner decision, 2026-11-07).** No `ManagedOOMPreference=`, no root helper for `oom_score_adj` (former Open Question 3). No limits of their own for `python3` processes or Claude Code sessions; a project that runs large test jobs moves them into its own unit, as done with `louie-pretest.service` (former Open Questions 5 and 6).
11. **Feature, group and role names and table values as recommended, no special case for VMs (owner decision, 2026-11-07).** Feature and group `memory-headroom`, role `memory_headroom`; preselected on private desktops, optional on work desktops, excluded on servers and in containers, not applied on a detected Raspberry Pi. VMs get no extra condition: the owner's remote workbench VMs are `device: server` and therefore excluded by the table, and a desktop VM may select the feature (former Open Question 7).
12. **Own feature and group, drop-ins in the user's home (owner decision, 2026-11-07).** As recommended under Alternatives considered: not an extension of `zram-swap`, not the group `systemd`, not `/etc/systemd/user/`.

## Implementation outline


- **Feature** `memory-headroom` in the feature table, help "Larger disk swap + slow Claude app instead of OOM kill", `groups: [memory-headroom]`, preselected on private desktops, optional on work desktops, excluded on servers and in containers (decision 11).
- **Role** `ansible/roles/memory_headroom`, applied in its own play in `ansible/workstation.yml` (tag `memory`) after the zram play, when `'memory-headroom' in machine_features` and `not (hw_pi | bool)`:
  - `defaults/main.yml`: `memory_headroom_swapfile: /swap.img`, `memory_headroom_swapfile_size_gib: 16`, `memory_headroom_min_free_gib: 20` (free space left after growing), `memory_headroom_oomd_pressure_limit: "80%"`, `memory_headroom_oomd_dropin: /etc/systemd/system/user@.service.d/90-oomd-limit.conf`, `memory_headroom_oomd_swap_dropin: /etc/systemd/system/-.slice.d/90-oomd-no-swap-kill.conf`.
  - oomd drop-in: a template with `[Service]` and `ManagedOOMMemoryPressureLimit={{ memory_headroom_oomd_pressure_limit }}`, mode 0644; handler `systemctl daemon-reload` when `machine_manage_services`. The new limit applies to running user managers after the reload; no logout is needed for oomd, which reads the unit property on reload (not verified yet).
  - Swap-kill drop-in (decision 9): a file with `[Slice]` and `ManagedOOMSwap=auto`, mode 0644, same handler.
  - Swap file: a small script `files/swapfile-grow` (installed to `machine_lib_dir`) that Ansible runs only when `machine_manage_services` is true. Ansible decides "changed" from its exit code. The script:
    1. Takes the target path and size. Uses the swap file listed in `/proc/swaps` with type `file` when there is exactly one; otherwise the configured path.
    2. Does nothing when the existing file is at least the target size (it never shrinks).
    3. Refuses with a warning, without changing anything, when the filesystem is not ext4 or xfs (btrfs needs `btrfs filesystem mkswapfile` and no copy-on-write), or when the free space after growing would be below `memory_headroom_min_free_gib` GiB or 5 % of the filesystem (the low-space threshold of spec `disk-space`).
    4. Creates `<path>.new` with `fallocate` (falling back to `dd` where `fallocate` is not supported for swap), mode 0600, `mkswap`, and `swapon` with the same priority as the old file (default -1 if none was active). Only then `swapoff` of the old file, so the pages of the old file always have somewhere to go. Then renames `<path>.new` to `<path>` (an active swap file can be renamed) and leaves the new file active.
    5. On any failure after step 4 started: `swapoff` and remove `<path>.new`, keep the old file active, exit non-zero with the reason.
  - `/etc/fstab`: makes sure one entry `<path> none swap sw 0 0` exists (`ansible.builtin.lineinfile`; `ansible.posix.mount` with `state: present` also fits and is the only allowed collection). The swap priority stays below zram's 100 because zram sets its own priority.
- **Dotfile group** `home/memory-headroom/.config/systemd/user/`:
  - `app-gnome-com.anthropic.Claude-.scope.d/50-memory-high.conf`
  - `app-com.anthropic.Claude-.scope.d/50-memory-high.conf`

  each with `[Scope]`, `MemoryHigh=8G` and `OOMPolicy=continue` (decision 5), and a comment that names this change. The existing `update timers` step reloads the user manager; the limit applies to the next start of the app (a running scope keeps its properties until then; `systemctl --user set-property` is not needed).
- **Docs**: a paragraph in `docs/features.md` (what the feature does, how to check: `swapon --show`, `systemctl show user@$(id -u).service -p ManagedOOMMemoryPressureLimit`, `systemctl --user show 'app-*Claude*' -p MemoryHigh`, `journalctl -k | grep -i oom`), the swap section of `docs/thinkpad-l13-yoga-gen2.md`, the role line in `Readme.md`, and `ansible/roles/memory_headroom/README.md` in the format of the other role READMEs.

## Alternatives considered

The owner confirmed the rejections below on 2026-11-07 (decision 12).

- **Extend the role and feature `zram-swap` instead of a new feature.** Rejected in the recommendation: `zram-swap` is preselected on servers, where neither the Claude app nor a 16 GiB swap file on the system disk is wanted, and its spec only says swap on disk stays in place. A separate feature can be deselected on its own.
- **Put the Claude drop-ins into the group `systemd`.** They would then reach every non-container host, servers included, independent of the swap and oomd settings. Harmless, but the three settings belong together: without the larger swap, `MemoryHigh` only moves the pressure. Rejected in the recommendation.
- **Deliver the Claude drop-ins with Ansible to `/etc/systemd/user/`.** Applies to all users of the host, but needs root and is skipped on hosts with `ansible: false`; the user unit belongs to the login user. Rejected in the recommendation.
- **Disable systemd-oomd for `user@.service` (`ManagedOOMMemoryPressure=auto`).** Removes the userspace safety net that kills a runaway app before the whole session freezes. Rejected (decision 8).
- **Swap size relative to RAM, to RAM plus zram, or to free disk space.** Rejected (decision 7).
- **`ManagedOOMPreference=avoid` in the Claude drop-ins, or a root helper that lowers the app's `oom_score_adj`.** Not in this change (decision 10).
- **Skip the feature on detected VMs (`hw_virtual`).** Rejected (decision 11).

## Testing

- `tests/unit/test_features.py`: `memory-headroom` is preselected on private desktops, optional on work desktops, not offered on servers and in containers, and selects the group `memory-headroom`.
- New `tests/unit/test_swapfile_grow.py` (pattern of `tests/unit/test_laptop_scripts.py`): the script runs against a fake `/proc/swaps`, a fake `df`/`stat` output and stub `fallocate`, `mkswap`, `swapon`, `swapoff` that log their calls:
  - a 4 GiB file is grown to 16 GiB in the order create, `mkswap`, `swapon` new, `swapoff` old, rename;
  - a file of 16 GiB or more is left alone and no command is called;
  - too little free space or btrfs: no command is called, a warning names the reason, exit code "unchanged";
  - `mkswap` or `swapon` of the new file fails: the old file stays active, `<path>.new` is removed, exit code non-zero;
  - no active swap file: the configured path is created.
- New `tests/unit/test_memory_headroom_role.py` (pattern of `tests/unit/test_monitoring_role.py`): the role, run on localhost with `machine_manage_services: false` and paths under `tmp_path`, writes the oomd drop-in with `ManagedOOMMemoryPressureLimit=80%`, the `-.slice` drop-in with `ManagedOOMSwap=auto` and the fstab line, and does not run the swap script; a second run reports no change.
- Dotfile group: a check (in `tests/unit/test_dotfiles.py` or the new role test) that both drop-ins exist, contain `[Scope]`, `MemoryHigh=8G` and `OOMPolicy=continue`, and that `systemd-analyze verify` accepts them where it is available (skip otherwise).
- Integration: `tests/hosts/ci-home-laptop.yml` gets `memory-headroom`; `tests/integration/test_host_yaml_install.py` asserts that both oomd drop-ins exist, that no swap file was created in the container, and that the second apply is idempotent.

## Risks / Trade-offs

- [`MemoryHigh` makes the Claude app the largest user of swap, and a swap-based systemd-oomd kill (`ManagedOOMSwap=kill` on `-.slice`) would then pick it first] → Ubuntu ships `ManagedOOMSwap=auto` (disabled) on homeserver and on the L13 (verified 2026-11-07), and the role enforces it (decision 9).
- [More swap on disk means the session can get very slow before anything is killed] → That is the owner's stated preference ("rather slower than killed"). systemd-oomd at 80 % pressure for 20 s still ends a true runaway.
- [`MemoryHigh` throttles regardless of free RAM, so a too-low value slows normal Claude Code work] → 8G is above the measured peak of 6.2 GB (decision 4); revisit if `memory.events` shows `high` events in normal use.
- [The kernel OOM killer can still pick the Claude app when RAM, zram and 16 GiB of disk swap are all full] → This happened six times on 2026-11-07 (see Verified on the L13). No unprivileged setting prevents the kill itself (see Context); with `OOMPolicy=continue` (decision 5) it ends one process instead of the whole app.
- [Growing the swap file costs 12 GiB of disk on the L13 and similar hosts] → The script keeps at least 20 GiB and 5 % free and never shrinks; the disk-space check warns independently.
- [A failure between `swapon` of the new file and the rename] → The old file is only turned off after the new one is active, and a failure rolls back to the old file.

## Migration Plan

On the L13 the three settings already exist:

- `/swap.img` is already 16 GiB, so the script leaves it alone.
- The role writes `/etc/systemd/system/user@.service.d/90-oomd-limit.conf` with the same content and name, which makes it Ansible-managed; etckeeper records no content change.
- The hand-made user drop-ins are regular files where the dotfile group wants symlinks. Before the first `machine apply` with the feature, remove `~/.config/systemd/user/app-gnome-com.anthropic.Claude-.scope.d/50-memory-high.conf` and `~/.config/systemd/user/app-com.anthropic.Claude-.scope.d/50-memory-high.conf`, or let the dotfile apply report the conflict (Assumptions).

ditschi-ThinkPad-T480 has no host config in `machine/hosts/`; it gets the feature on its next `machine setup` with the private desktop defaults. Rollback: deselect the feature or revert the change; the role does not remove the drop-in or shrink the swap file, which the owner does by hand if wanted (`docs/features.md` describes how).

## Verified on the L13 (task 1.1, 2026-11-07)

Checked on ThinkPad-L13-Yoga-Gen-2 (systemd 259.5-0ubuntu3.4, Claude desktop app running):

- Prefix drop-ins apply to scopes: `DropInPaths` of every `app-com.anthropic.Claude-<id>.scope` and `app-gnome-com.anthropic.Claude-<id>.scope` lists the hand-made `~/.config/systemd/user/<prefix>-.scope.d/50-memory-high.conf`, and `MemoryHigh` reports 8589934592 (8 GiB).
- The memory controller is delegated to the user manager (`cgroup.controllers` of `user@1000.service`: `cpu memory pids`), and the limit takes effect: `memory.high` of the running scopes is 8589934592.
- `user@1000.service` has `ManagedOOMMemoryPressure=kill` and `ManagedOOMMemoryPressureLimit=3435973836`, which is 80 % of 2^32, from `/etc/systemd/system/user@.service.d/90-oomd-limit.conf` on top of Ubuntu's `10-oomd-user-service-defaults.conf`.
- `swapon --show`: `/dev/zram0` 7.4G at priority 100, `/swap.img` 16G at priority -1.
- `-.slice` has `ManagedOOMSwap=auto`, set by Ubuntu's `/usr/lib/systemd/system/-.slice.d/10-oomd-root-slice-defaults.conf`, so swap-based systemd-oomd kills are off (decision 9).
- `systemd.resource-control(5)` of systemd 259 describes `ManagedOOMPreference=` for user cgroups word for word as systemd 255 does (see Context).
- Claude scopes have `OOMPolicy=stop` (the user manager's `DefaultOOMPolicy=stop`). `systemd.scope(5)` of systemd 259 documents `OOMPolicy=` for scopes: with `stop`, systemd stops the whole unit when the kernel OOM killer kills any one of its processes; with `continue`, the unit keeps running.

Incidents after the hand-made settings were in place (kernel log and user journal, 2026-11-07): global kernel OOMs at 09:36, 09:39, 09:42, 10:27, 17:50 and 18:01. Victims: `claude-desktop` renderers (`oom_score_adj` 300), a VS Code process (snap scope) and `python3` test runs with 0.6 to 3.4 GB RSS (`oom_score_adj` 100). The `python3` processes ran inside `app-com.anthropic.Claude-<id>.scope`: commands that Claude Code sessions start inherit the app's scope. After each kill, systemd ended the whole Claude scope (`Failed with result 'oom-kill'`, every remaining process SIGKILLed), so the app was gone even when only a `python3` child had been picked. The ended scopes report peaks of 7.9G memory with 16.5G swap, and 7.4G memory with 14.8G swap. RAM, zram and the 16 GiB swap file were all full. No systemd-oomd kill was logged. The `python3` test runs of that project have since been moved by hand into a transient user unit `louie-pretest.service` with `MemoryMax=6G` and `OOMScoreAdjust=200`, outside the Claude scope (decision 10).

## Assumptions
- The Claude desktop app is started as a scope named `app-gnome-com.anthropic.Claude-<id>.scope` from the GNOME launcher and `app-com.anthropic.Claude-<id>.scope` otherwise, as seen in the journals on 2026-11-06. Another packaging (for example a Snap or Flatpak) may use other scope names.
- systemd follows the symlinks that the dotfile group creates for drop-in files, as it does for the existing user units of the group `systemd`.
- The dotfile apply reports a regular file where it wants a symlink as a conflict instead of overwriting it silently; to be checked against the dotfile apply before the migration.
- Ubuntu installs swap as the file `/swap.img` on ext4, as on the L13; hosts installed differently (swap partition, btrfs) are skipped with a warning by the script.
- Firefox content processes already run with a raised `oom_score_adj`; not verified (only relevant for later protection work, decision 10).

## Open Questions

None. The owner answered all of them on 2026-11-07 (decisions 5-12).
