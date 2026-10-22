# Proposal

## Why

System provisioning with Ansible roles and features is the eleventh and last area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- Ansible was chosen because its playbooks are readable. It is new to the owner, so a clearly better and approachable alternative stays worth evaluating.
- System tools should be maintainable and updateable across machines, alongside the dotfiles. New-host setup guides choices and existing-host updates make the applied changes clear.

## What Changes

- Describe the confirmed behaviour as baseline requirements: Ansible driven by the feature list, the package table and local roles, Node tools, the LLM CLI features, automatic OpenSpec install, preserving existing installations, the need for root, and the collection policy.
- Alternatives and open decisions stay out of the specs and become investigations in design.md: comparing provisioners, a privileged route for managed work machines, Node per profile, OpenSpec as an explicit feature, the purpose of `etckeeper`, and remote updates.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `system-provisioning`: how Ansible applies packages, tools and system configuration for a host's features.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0011-system-provisioning (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
