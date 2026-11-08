# Spec Delta

## ADDED Requirements

### Requirement: Swap file on disk grown to the target size
With the feature `memory-headroom`, the swap file on disk SHALL be at least the target size: the RAM rounded down to whole GiB plus 2 GiB, configurable per host. A larger swap file SHALL be left as it is. The swap file SHALL keep a lower swap priority than zram and SHALL be activated at boot.

#### Scenario: Laptop with a 4 GiB swap file
- **WHEN** a host with `memory-headroom` and 14.8 GiB of RAM has a 4 GiB `/swap.img`, enough free disk space and enough free RAM, and `machine apply` runs
- **THEN** `/swap.img` is 16 GiB, active, listed in `/etc/fstab`, and used after zram

#### Scenario: Swap file already large enough
- **WHEN** the swap file is at least the target size
- **THEN** it is not changed and nothing is reported as changed

### Requirement: Swap file grown only with room in RAM
The swap file SHALL be turned off for growing only when free RAM holds its used swap plus 2 GiB. Otherwise it SHALL keep its size, Ansible SHALL print a warning with the commands to grow it by hand, the run SHALL go on, and the next run SHALL try again. When a step fails or the run is interrupted after the file was turned off, the swap file SHALL be turned on again and the failure SHALL be reported.

#### Scenario: Busy host
- **WHEN** the swap file holds 3 GiB of used swap and 4 GiB of RAM are available
- **THEN** the swap file keeps its size, a warning names the free RAM and the commands to grow it by hand, and the run does not fail

#### Scenario: mkswap fails
- **WHEN** formatting the grown swap file fails
- **THEN** the swap file is active again and the Ansible run reports the failure

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
With the feature `memory-headroom`, every scope of the Claude desktop app SHALL have `MemoryHigh=8G`, whether it is started from the GNOME launcher or otherwise, so that its memory is reclaimed into swap first when it grows beyond that.

#### Scenario: App started from GNOME
- **WHEN** the Claude desktop app is started from the GNOME launcher on a host with `memory-headroom`
- **THEN** its scope reports `MemoryHigh` of 8 GiB

#### Scenario: App not installed
- **WHEN** the host has no Claude desktop app
- **THEN** the setting has no effect and no unit fails

#### Scenario: App running during apply
- **WHEN** the app is running while `machine apply` adds the setting
- **THEN** the app keeps running, and the limit applies from its next start

### Requirement: Claude desktop app survives a kill of one of its processes
With the feature `memory-headroom`, every scope of the Claude desktop app SHALL have `OOMPolicy=continue`, so that systemd does not stop the whole app when the kernel OOM killer kills one process in its scope.

#### Scenario: Test run of a Claude Code session killed
- **WHEN** the kernel OOM killer kills a `python3` process that a Claude Code session started inside the app's scope
- **THEN** only that process ends, and the app and its other Claude Code sessions keep running

### Requirement: No swap-based systemd-oomd kills
With the feature `memory-headroom`, `-.slice` SHALL have `ManagedOOMSwap=auto`, configured in its own drop-in, so that systemd-oomd does not kill a cgroup because of its swap use, also if a distribution default enables it.

#### Scenario: Swap almost full
- **WHEN** RAM and swap are more than 90 % used and the Claude app holds the most swap
- **THEN** systemd-oomd does not kill the app's scope for its swap use
