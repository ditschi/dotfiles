# Spec Delta

## ADDED Requirements

### Requirement: Memory headroom as a local role
The swap file size, the systemd-oomd limit for user sessions and the systemd-oomd swap setting of `-.slice` of the feature `memory-headroom` SHALL be applied by the local role `memory_headroom`, which needs root. The memory limit and the OOM policy of the Claude desktop app SHALL be dotfiles of the group `memory-headroom` and SHALL need no root.

#### Scenario: Host without root
- **WHEN** a host with `memory-headroom` sets `ansible: false`
- **THEN** the Claude app settings are still applied, and the swap file and the oomd settings are not changed
