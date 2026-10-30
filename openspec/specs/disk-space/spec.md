# disk-space Specification

## Purpose

Warns the user about local filesystems that run low on space or inodes, through `machine attention`, the shell prompt and `machine status`, on every host and with no configuration needed for hosts with several disks.

## Requirements

### Requirement: Watched filesystems
`machine` SHALL watch every mounted read-write filesystem of type ext4, xfs, btrfs or vfat. A device mounted more than once (bind mounts, btrfs subvolumes) SHALL be watched once, under its shortest mount point. Other filesystem types (tmpfs, overlay, squashfs, network filesystems) SHALL NOT be watched unless the host config names their mount point. The check SHALL be always on, without a feature.

#### Scenario: VM with system and data disk
- **WHEN** a host has an ext4 `/` and an ext4 data disk mounted at `/mnt/data`
- **THEN** both `/` and `/mnt/data` are watched without any host configuration

#### Scenario: Same device mounted twice
- **WHEN** one device is mounted at `/mnt/data` and bind-mounted at `/srv/data`
- **THEN** it is watched once, as `/mnt/data`

#### Scenario: Container
- **WHEN** the root filesystem is an overlay, as in a container
- **THEN** it is not watched, and nothing is reported for it

#### Scenario: Read-only mount
- **WHEN** an ext4 filesystem is mounted read-only
- **THEN** it is not watched

### Requirement: Low-space threshold
A watched filesystem SHALL be low on space when the space available to the user is below 5 % of its size and below 20 GiB. It SHALL be low on inodes when it reports inodes and fewer than 5 % of them are free. The check SHALL read the current values every time it runs.

#### Scenario: Large disk with enough absolute space
- **WHEN** a 2 TiB filesystem has 60 GiB free (3 %)
- **THEN** it is not low, because 60 GiB is not below 20 GiB

#### Scenario: Small boot partition
- **WHEN** a 2 GiB `/boot` has 80 MiB free (4 %)
- **THEN** it is low on space

#### Scenario: Out of inodes
- **WHEN** an ext4 filesystem has plenty of free space and 2 % free inodes
- **THEN** it is low on inodes

#### Scenario: Filesystem without inode counts
- **WHEN** a filesystem reports no inode counts, as vfat and btrfs do
- **THEN** only its space is checked

#### Scenario: Space freed
- **WHEN** a low filesystem gets enough space again
- **THEN** the next check no longer reports it

### Requirement: Threshold per mount point
The host config key `disk_space` SHALL be an optional list of entries with a `path` (a mount point) and either thresholds (`min_free` as a size such as `100G`, `min_free_percent`) or `ignore: true`. Thresholds given for a mount point SHALL replace both default space thresholds, and the filesystem SHALL be low when it is below every threshold given. An ignored mount point SHALL never be reported. A named mount point SHALL be watched whatever its type.

#### Scenario: Larger reserve for the data disk
- **WHEN** ABTVL421 sets `min_free: 100G` for `/mnt/data` and `/mnt/data` has 80 GiB free of 2 TiB
- **THEN** `/mnt/data` is low on space

#### Scenario: Ignored scratch disk
- **WHEN** the host config sets `ignore: true` for `/mnt/scratch` and it is full
- **THEN** no item is reported for it

#### Scenario: Named mount point not mounted
- **WHEN** the host config names a mount point that is not mounted
- **THEN** it is skipped without an error

#### Scenario: Invalid entry
- **WHEN** an entry has no `path` or an unreadable size
- **THEN** `machine` warns, names the entry and uses the defaults for the rest

### Requirement: Disk attention item
`machine attention` SHALL list one `disk` item per low filesystem. The item SHALL name the mount point, the percentage used, and the free and total space (or the free inodes). It SHALL be computed live, so it disappears as soon as the filesystem is no longer low.

#### Scenario: Data disk full
- **WHEN** `/mnt/data` is low on space and the user runs `machine attention`
- **THEN** an item reads like `[disk] /mnt/data is 97 % full (12 GiB free of 500 GiB)`

#### Scenario: Two low filesystems
- **WHEN** `/` and `/mnt/data` are both low
- **THEN** two separate items are listed

### Requirement: Guided cleanup
In a terminal, the disk item SHALL show the sizes of the known space users that are on the low filesystem: Docker data when the host has the feature `docker`, the systemd journal, the apt cache, `~/.cache` and the mise cache. It SHALL offer the matching cleanups, a scan of the biggest directories, and doing nothing (the default). Nothing SHALL be deleted without the user picking that cleanup. Commands that need root SHALL run with `sudo`.

#### Scenario: Cleanup chosen
- **WHEN** the user picks the cleanup of the apt cache and the journal
- **THEN** those two are cleaned, and the free space afterwards is shown

#### Scenario: Nothing chosen
- **WHEN** the user accepts the default
- **THEN** nothing is deleted and the item stays open

#### Scenario: Space user on another filesystem
- **WHEN** Docker data is on `/` and the low filesystem is `/mnt/data`
- **THEN** the Docker cleanup is not offered for `/mnt/data`

#### Scenario: Directory scan only on request
- **WHEN** the item is shown
- **THEN** no directory scan runs until the user picks it; the scan stays on the low filesystem

#### Scenario: No terminal
- **WHEN** `machine attention` runs without a terminal
- **THEN** the disk items are listed and no sizes are measured and nothing is cleaned

### Requirement: Recorded disk state
`machine` SHALL record the low filesystems in a state file that the shell can read without starting a process. A user timer SHALL record them every 15 minutes, and every `machine` run SHALL record them too. The timer SHALL never prompt and SHALL NOT clean anything.

#### Scenario: Disk fills between runs
- **WHEN** `/mnt/data` becomes low and no `machine` command runs
- **THEN** the state file names it within 15 minutes

#### Scenario: Space freed through the item
- **WHEN** the user frees space in `machine attention`
- **THEN** the state file no longer names the filesystem when the command ends

### Requirement: Disk prompt segment
Interactive zsh and bash SHALL show a disk segment while the recorded state names a low filesystem, for example `⚠ disk /mnt/data 97%`. With several low filesystems, the segment SHALL name all of them. The segment SHALL be separate from the update segment, re-evaluated after each command, and SHALL disappear when the state no longer names a low filesystem.

#### Scenario: Low data disk
- **WHEN** the state names `/mnt/data` as 97 % full
- **THEN** the prompt shows `⚠ disk /mnt/data 97%`

#### Scenario: Update and disk at once
- **WHEN** an update is available and a filesystem is low
- **THEN** the prompt shows both segments

#### Scenario: Nothing low
- **WHEN** the state names no low filesystem
- **THEN** no disk segment is shown

### Requirement: Disk line in the status
`machine status` SHALL show one line naming the low filesystems with their usage, and the hint to run `machine attention`, when a filesystem is low. Without a low filesystem it SHALL show no disk line.

#### Scenario: Status with a low disk
- **WHEN** `/mnt/data` is low and the user runs `machine status`
- **THEN** one line names `/mnt/data` with its usage and `machine attention`
