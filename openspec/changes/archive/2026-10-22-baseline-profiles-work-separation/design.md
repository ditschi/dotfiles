# Design

## Context

This change writes the confirmed profile and work/private behaviour down as baseline specs and changes no code. See proposal.md for the motivation. Current code: profiles and environment groups are defined in `machine_cli/core.py`, the default profile in `machine_cli/profile.py` (`default_profile`), the shell side in `home/dot_zsh/machine-profile.sh`, and linking in `home/.chezmoiignore`.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep unclear points visible as investigations.

**Non-Goals:**
- Fixes or improvements.

## Decisions

1. **Profiles carry defaults, host files carry the choice.** Each host has one profile with feature defaults, and its own file records the profile and features.
2. **Work and private are separated by profile and group.** Work-only tools and secrets are limited by profile, environment group, Git identity and SSH key class.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Order of the default profile checks.** The current order is accepted. The owner is unsure whether the saved profile or Docker should come first. Suggestion: evaluate cases where a host profile is saved inside a container or a host is mistaken for a container. Why: a wrong `container` profile on a real host would silently drop its setup.
2. **Container always gets the container setup.** The owner's gut feeling: inside a container the container flavoured setup should always apply. Suggestion: let container detection win over a saved or inherited profile, after investigation 1. Why: containers share the home directory or environment of a host and should not inherit its profile.
3. **Group pattern beyond environment files.** Environment files already use groups. Suggestion: check whether the same pattern fits other places that now key on a single profile. Why: groups let one host belong to several areas without new profiles.
4. **`WORK_SETUP` in dev containers.** The owner wants dev containers to enable nothing work-specific, but the shell may still set it there for a company user ID. Suggestion: list every place that sets or reads it in containers and stop setting it there. Why: removes work behaviour from environments that should be neutral.
5. **Work detection signals.** Suggestion: compare user name, hostname, domain and saved profile on known hosts and containers. Why: a single weak signal can misclassify a host.
6. **Profile versus feature.** The boundary is not settled. Suggestion: list how current hosts use both and where they overlap. Why: a clear boundary decides where new settings belong.
7. **Sensitive details in the repository.** Suggestion: keep generic logic and sanitized examples in the repository and move real work identity, internal endpoints and network details to local configuration. Public keys and homelab identifiers are deliberate disclosures. Why: the repository is meant to be shareable.
