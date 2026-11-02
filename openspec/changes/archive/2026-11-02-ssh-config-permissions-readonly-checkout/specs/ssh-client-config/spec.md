# Spec Delta

## MODIFIED Requirements

### Requirement: Config file mode
`machine apply` SHALL make the versioned base config not writable for group and others, so that ssh accepts the linked file on every distribution. When the checkout is on a read-only file system, it SHALL report that the mode could not be changed and SHALL NOT fail for that reason.

#### Scenario: Checkout with umask 002
- **WHEN** the repository file has mode 664 and `machine apply` runs
- **THEN** the file has mode 644 afterwards and ssh reads it

#### Scenario: Read-only checkout
- **WHEN** the repository file has mode 664, the checkout is on a read-only file system and `machine apply` runs
- **THEN** the apply continues, the output says that write access could not be removed, and the managed known-hosts file is still written
