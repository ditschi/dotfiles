# Design

## Context

See proposal.md for the owner-selection need. The existing GitHub rules select identity from remote URLs and support `bosch-*` and `bosch_*` owners. The shared configuration must continue to work independently of clone path.

## Goals / Non-Goals

**Goals:** recognize GitHub owners ending in `_bosch` for HTTPS and SCP-style SSH remotes while preserving existing work and private matching.

**Non-Goals:** changing credentials, host profiles, repository remotes, or the GitHub identity rules for unrelated owners.

## Decisions

- Extend the existing remote-owner include rules with an end-anchored `*_bosch` pattern for HTTPS and SCP-style SSH URLs. This keeps work identity selection tied to the remote owner and consistent across clone paths.
- Match only the owner component. A repository name ending in `_bosch`, or an owner that merely contains `_bosch`, must not select work identity.
- Clone-path matching is not used because the existing requirement makes remote URL ownership authoritative and independent of checkout location.

## Risks / Trade-offs

- A broad or unanchored pattern could classify private owners as work. Match the suffix at the owner boundary and cover negative cases in tests.

## Migration Plan

No migration is required. Existing owners retain their current identity selection; affected clones select work identity on their next Git operation.
