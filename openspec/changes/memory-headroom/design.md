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
- `ManagedOOMSwap=kill` on `-.slice` makes systemd-oomd kill the cgroup with the most swap when memory and swap use both exceed `SwapUsedLimit=` (default 90 %). On homeserver (Ubuntu, systemd 255) the shipped drop-in sets `ManagedOOMSwap=auto`, which disables this; the L13 value is not verified.
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
- Limiting Firefox, `python3` processes or Claude Code sessions (Open Questions 5 and 6).
- Hibernation (needs swap of at least the RAM size and other configuration; S3 made it unnecessary on the L13).

## Decisions

1. **The three settings are reproduced as the owner applied them on the L13.** Swap file on disk at 16 GiB with priority below zram, `ManagedOOMMemoryPressureLimit=80%` for `user@.service`, and `MemoryHigh=4G` for every scope of the Claude desktop app, both under the GNOME launcher name (`app-gnome-com.anthropic.Claude-`) and the plain one (`app-com.anthropic.Claude-`).
2. **The Claude app is slowed down, never killed by the dotfiles' own settings.** Nothing in this change kills, stops or restarts the app; every setting either adds room (swap) or throttles (`MemoryHigh`).
3. **Containers never get it.** A container sees the host's memory and swap and has no own systemd user manager to configure.

## Implementation outline

This outline follows the recommended options in Open Questions; task 0 confirms or changes them before any code is written.

- **Feature** `memory-headroom` in the feature table, help "Larger disk swap + slow Claude app instead of OOM kill", `groups: [memory-headroom]`, preselected on private desktops, optional on work desktops, excluded on servers and in containers (Open Question 7).
- **Role** `ansible/roles/memory_headroom`, applied in its own play in `ansible/workstation.yml` (tag `memory`) after the zram play, when `'memory-headroom' in machine_features` and `not (hw_pi | bool)`:
  - `defaults/main.yml`: `memory_headroom_swapfile: /swap.img`, `memory_headroom_swapfile_size_gib: 16`, `memory_headroom_min_free_gib: 20` (free space left after growing), `memory_headroom_oomd_pressure_limit: "80%"`, `memory_headroom_oomd_dropin: /etc/systemd/system/user@.service.d/90-oomd-limit.conf`.
  - oomd drop-in: a template with `[Service]` and `ManagedOOMMemoryPressureLimit={{ memory_headroom_oomd_pressure_limit }}`, mode 0644; handler `systemctl daemon-reload` when `machine_manage_services`. The new limit applies to running user managers after the reload; no logout is needed for oomd, which reads the unit property on reload (to be verified, task 1).
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

  each with `[Scope]` and `MemoryHigh=4G` and a comment that names this change. The existing `update timers` step reloads the user manager; the limit applies to the next start of the app (a running scope keeps its properties until then; `systemctl --user set-property` is not needed).
- **Docs**: a paragraph in `docs/features.md` (what the feature does, how to check: `swapon --show`, `systemctl show user@$(id -u).service -p ManagedOOMMemoryPressureLimit`, `systemctl --user show 'app-*Claude*' -p MemoryHigh`, `journalctl -k | grep -i oom`), the swap section of `docs/thinkpad-l13-yoga-gen2.md`, the role line in `Readme.md`, and `ansible/roles/memory_headroom/README.md` in the format of the other role READMEs.

## Alternatives considered

These are listed for the owner's decision in task 0; none of them is owner-confirmed yet.

- **Extend the role and feature `zram-swap` instead of a new feature.** Rejected in the recommendation: `zram-swap` is preselected on servers, where neither the Claude app nor a 16 GiB swap file on the system disk is wanted, and its spec only says swap on disk stays in place. A separate feature can be deselected on its own.
- **Put the Claude drop-ins into the group `systemd`.** They would then reach every non-container host, servers included, independent of the swap and oomd settings. Harmless, but the three settings belong together: without the larger swap, `MemoryHigh` only moves the pressure. Rejected in the recommendation.
- **Deliver the Claude drop-ins with Ansible to `/etc/systemd/user/`.** Applies to all users of the host, but needs root and is skipped on hosts with `ansible: false`; the user unit belongs to the login user. Rejected in the recommendation.
- **Disable systemd-oomd for `user@.service` (`ManagedOOMMemoryPressure=auto`).** Removes the userspace safety net that kills a runaway app before the whole session freezes. Rejected in the recommendation (Open Question 4).
- **Swap size relative to RAM or to free disk space.** See Open Question 1.

## Testing

- `tests/unit/test_features.py`: `memory-headroom` is preselected on private desktops, optional on work desktops, not offered on servers and in containers, and selects the group `memory-headroom`.
- New `tests/unit/test_swapfile_grow.py` (pattern of `tests/unit/test_laptop_scripts.py`): the script runs against a fake `/proc/swaps`, a fake `df`/`stat` output and stub `fallocate`, `mkswap`, `swapon`, `swapoff` that log their calls:
  - a 4 GiB file is grown to 16 GiB in the order create, `mkswap`, `swapon` new, `swapoff` old, rename;
  - a file of 16 GiB or more is left alone and no command is called;
  - too little free space or btrfs: no command is called, a warning names the reason, exit code "unchanged";
  - `mkswap` or `swapon` of the new file fails: the old file stays active, `<path>.new` is removed, exit code non-zero;
  - no active swap file: the configured path is created.
- New `tests/unit/test_memory_headroom_role.py` (pattern of `tests/unit/test_monitoring_role.py`): the role, run on localhost with `machine_manage_services: false` and paths under `tmp_path`, writes the oomd drop-in with `ManagedOOMMemoryPressureLimit=80%` and the fstab line, and does not run the swap script; a second run reports no change.
- Dotfile group: a check (in `tests/unit/test_dotfiles.py` or the new role test) that both drop-ins exist, contain `[Scope]` and `MemoryHigh=4G`, and that `systemd-analyze verify` accepts them where it is available (skip otherwise).
- Integration: `tests/hosts/ci-home-laptop.yml` gets `memory-headroom`; `tests/integration/test_host_yaml_install.py` asserts the oomd drop-in exists, that no swap file was created in the container, and that the second apply is idempotent.

## Risks / Trade-offs

- [`MemoryHigh` makes the Claude app the largest user of swap, and a swap-based systemd-oomd kill (`ManagedOOMSwap=kill` on `-.slice`) would then pick it first] → On homeserver the shipped default is `ManagedOOMSwap=auto` (disabled). Task 1 checks the value on the L13 and the T480; if it is `kill`, task 0 decides whether the role also sets `ManagedOOMSwap=auto` on `-.slice`.
- [More swap on disk means the session can get very slow before anything is killed] → That is the owner's stated preference ("rather slower than killed"). systemd-oomd at 80 % pressure for 20 s still ends a true runaway.
- [`MemoryHigh` throttles the app hard when its working set alone exceeds 4 GiB] → The observed size was about 1.7 GB; Open Question 2.
- [The kernel OOM killer can still pick the Claude app when RAM, zram and 16 GiB of disk swap are all full] → No unprivileged setting prevents that (see Context); Open Question 3.
- [Growing the swap file costs 12 GiB of disk on the L13 and similar hosts] → The script keeps at least 20 GiB and 5 % free and never shrinks; the disk-space check warns independently.
- [A failure between `swapon` of the new file and the rename] → The old file is only turned off after the new one is active, and a failure rolls back to the old file.

## Migration Plan

On the L13 the three settings already exist:

- `/swap.img` is already 16 GiB, so the script leaves it alone.
- The role writes `/etc/systemd/system/user@.service.d/90-oomd-limit.conf` with the same content and name, which makes it Ansible-managed; etckeeper records no content change.
- The hand-made user drop-ins are regular files where the dotfile group wants symlinks. Before the first `machine apply` with the feature, remove `~/.config/systemd/user/app-gnome-com.anthropic.Claude-.scope.d/50-memory-high.conf` and `~/.config/systemd/user/app-com.anthropic.Claude-.scope.d/50-memory-high.conf`, or let the dotfile apply report the conflict (Assumptions).

ditschi-ThinkPad-T480 has no host config in `machine/hosts/`; it gets the feature on its next `machine setup` with the private desktop defaults. Rollback: deselect the feature or revert the change; the role does not remove the drop-in or shrink the swap file, which the owner does by hand if wanted (`docs/features.md` describes how).

## Assumptions

- systemd 259 on the L13 behaves as documented for systemd 255 for prefix drop-ins of scopes, `MemoryHigh=` in user scopes, `ManagedOOMMemoryPressureLimit=` and `ManagedOOMPreference=`; task 1 verifies this on the L13.
- The Claude desktop app is started as a scope named `app-gnome-com.anthropic.Claude-<id>.scope` from the GNOME launcher and `app-com.anthropic.Claude-<id>.scope` otherwise, as seen in the journals on 2026-11-06. Another packaging (for example a Snap or Flatpak) may use other scope names.
- The user manager on Ubuntu has the memory controller delegated, so `MemoryHigh=` in a user scope takes effect (the owner's hand-made drop-ins were applied, but whether they took effect was not checked before this change was written).
- systemd follows the symlinks that the dotfile group creates for drop-in files, as it does for the existing user units of the group `systemd`.
- The dotfile apply reports a regular file where it wants a symlink as a conflict instead of overwriting it silently; to be checked against the dotfile apply before the migration.
- Ubuntu installs swap as the file `/swap.img` on ext4, as on the L13; hosts installed differently (swap partition, btrfs) are skipped with a warning by the script.
- Firefox content processes already run with a raised `oom_score_adj`; not verified (Open Question 3).

## Open Questions

1. **Swap size rule.** Recommended: a fixed 16 GiB (variable `memory_headroom_swapfile_size_gib`), grow only, and skip when less than 20 GiB and 5 % of the filesystem would remain free. Reason: 16 GiB is the size proven on the L13, and the free-space guard protects small disks without a formula that nobody has validated. Alternatives: the RAM size (14 GiB on the L13), RAM plus zram, or a share of the free disk space.
2. **`MemoryHigh=4G` on hosts with less or more RAM.** Recommended: keep the fixed 4G. Reason: it is sized from the app's own working set (about 1.7 GB observed), not from the host; a percentage (`MemoryHigh=` accepts a share of physical RAM, 4G is about 29 % on the L13) would throttle the app on an 8 GB host and do nothing useful on a 32 GB host. Revisit if the app grows beyond 3 GB in normal use.
3. **Further protection of the Claude app.** Recommended: none in this change; measure first. Facts found: an unprivileged user cannot lower `oom_score_adj` below the minimum a privileged process set (`proc_pid_oom_score_adj(5)`), so the user cannot protect the app from the kernel OOM killer. `ManagedOOMPreference=avoid` is not simply ignored for user cgroups: per `systemd.resource-control(5)` (systemd 255) it is respected for memory-pressure kills when the cgroup and the monitored ancestor have the same owner (Claude scope under `user@.service`), and ignored for swap-based kills on `-.slice`. Options for later: `ManagedOOMPreference=avoid` in the same Claude drop-ins (cheap; verify on systemd 259 in task 1), raising the `oom_score_adj` of Firefox content processes from the user side (allowed, but needs a watcher, because `OOMScoreAdjust=` is an exec setting and not available for scopes), or a root-side setting through Ansible that lowers the Claude app's `oom_score_adj` (needs a root helper per app start).
4. **oomd limit 80 % or oomd off for `user@.service`.** Recommended: 80 % as applied on the L13. Reason: it keeps systemd-oomd as the safety net for a runaway process while tolerating the swapping that the larger swap file allows. Turning oomd off for user sessions would leave only the kernel OOM killer, which picked the Claude app in the incident.
5. **The `python3` process (about 1.1 GB).** Recommended: no limit now; find out which program it was before deciding. Reason: unknown process, and a limit without knowing its scope name would not apply.
6. **Claude Code sessions (0.3-0.5 GB each).** Recommended: no own limit now. Reason: they run in terminal scopes (for example of GNOME Terminal or VS Code) that hold the shell and other tools too, so a limit there throttles more than Claude Code; with the larger swap, several sessions fit.
7. **Feature name, table values and hosts.** Recommended: feature and group `memory-headroom`, role `memory_headroom`; preselected on private desktops, optional on work desktops, excluded on servers and in containers, and not applied on a detected Raspberry Pi. Reason: the owner named laptops and desktops (the T480 and future reinstalls); work hosts may have small or managed disks; servers run other workloads (for example Kubernetes, which expects little or no swap). Open sub-question: should it also be skipped on a detected VM (`hw_virtual`), such as the work VM?
8. **`ManagedOOMSwap=` on `-.slice`.** If task 1 finds `kill` on the L13 or the T480, should the role set it to `auto` there? Recommended: yes, with a drop-in under `/etc/systemd/system/-.slice.d/`, because otherwise the throttled Claude app is the first swap-based kill candidate.
