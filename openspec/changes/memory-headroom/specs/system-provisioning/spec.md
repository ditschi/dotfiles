# Spec Delta

## ADDED Requirements

### Requirement: Memory headroom as a local role
The swap file size and the systemd-oomd limit for user sessions of the feature `memory-headroom` SHALL be applied by the local role `memory_headroom`, which needs root. The memory limit of the Claude desktop app SHALL be a dotfile of the group `memory-headroom` and SHALL need no root.

#### Scenario: Host without root
- **WHEN** a host with `memory-headroom` sets `ansible: false`
- **THEN** the Claude app limit is still applied, and the swap file and the oomd limit are not changed
