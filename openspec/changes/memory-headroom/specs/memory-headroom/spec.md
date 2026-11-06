# Spec Delta

## ADDED Requirements

### Requirement: Swap file on disk grown to the target size
With the feature `memory-headroom`, the swap file on disk SHALL be at least the target size, 16 GiB by default and configurable per host. A larger swap file SHALL be left as it is. The swap file SHALL keep a lower swap priority than zram and SHALL be activated at boot.

#### Scenario: Laptop with a 4 GiB swap file
- **WHEN** a host with `memory-headroom` has a 4 GiB `/swap.img` and enough free disk space, and `machine apply` runs
- **THEN** `/swap.img` is 16 GiB, active, listed in `/etc/fstab`, and used after zram

#### Scenario: Swap file already large enough
- **WHEN** the swap file is 16 GiB or larger
- **THEN** it is not changed and nothing is reported as changed

### Requirement: Swap file resized without losing swap
Growing the swap file SHALL activate the new swap space before the old one is turned off. When any step fails, the old swap file SHALL stay active and no partial file SHALL remain.

#### Scenario: mkswap fails
- **WHEN** preparing the new swap file fails
- **THEN** the old swap file is still active, the partial file is removed, and the Ansible run reports the failure

### Requirement: Swap file not grown without room
The swap file SHALL NOT be grown when less than 20 GiB or less than 5 % of the filesystem would remain free afterwards, or when the filesystem does not support a swap file created this way. The host SHALL then keep its swap unchanged and Ansible SHALL print a warning that names the reason, without failing the run.

#### Scenario: Small disk
- **WHEN** growing the swap file would leave 10 GiB free
- **THEN** the swap file keeps its size and a warning names the free space

#### Scenario: btrfs root
- **WHEN** the swap file lies on btrfs
- **THEN** the swap file keeps its size and a warning names the filesystem

### Requirement: Swap changes only on real hosts
The swap file SHALL NOT be created, grown or activated in containers, in CI and on a detected Raspberry Pi.

#### Scenario: CI laptop container
- **WHEN** the CI laptop host with `memory-headroom` is applied in a Docker container
- **THEN** no swap file is created and the run does not fail

### Requirement: User sessions tolerate memory pressure longer
With the feature `memory-headroom`, systemd-oomd SHALL act on a user session's memory pressure only above 80 %, configured in its own drop-in for `user@.service`, so that a system package update does not reset it.

#### Scenario: Swapping under load
- **WHEN** the user session's memory pressure stays between 50 % and 80 % for longer than 20 s
- **THEN** systemd-oomd kills nothing in the session

#### Scenario: Runaway process
- **WHEN** the memory pressure stays above 80 % for the configured duration
- **THEN** systemd-oomd still acts on the session

### Requirement: Claude desktop app throttled instead of killed
With the feature `memory-headroom`, every scope of the Claude desktop app SHALL have `MemoryHigh=4G`, whether it is started from the GNOME launcher or otherwise, so that its memory is reclaimed into swap first when it grows beyond that.

#### Scenario: App started from GNOME
- **WHEN** the Claude desktop app is started from the GNOME launcher on a host with `memory-headroom`
- **THEN** its scope reports `MemoryHigh` of 4 GiB

#### Scenario: App not installed
- **WHEN** the host has no Claude desktop app
- **THEN** the setting has no effect and no unit fails

#### Scenario: App running during apply
- **WHEN** the app is running while `machine apply` adds the setting
- **THEN** the app keeps running, and the limit applies from its next start
