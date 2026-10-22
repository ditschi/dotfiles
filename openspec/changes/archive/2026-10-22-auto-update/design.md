## Context

The timer today only fetches and sets a marker. `machine update` applies Ansible only on `--system` or a changed profile and cannot run unattended with `become` unless sudo is passwordless.

## Decisions

- Unattended scope: automatic fast-forward pull and chezmoi apply, only when the checkout is clean (after the resolvers) and only home files changed. System or profile changes are only shown by the indicator.
- Mixed home and system changes: the background job walks the incoming commits in order and fast-forwards only to just before the first commit that touches `ansible/**`, packages or the host profile. That commit and everything after it stay pending for a manual `machine update`. Shell extensions that need something installed by Ansible are therefore never applied before their system step. A commit that touches both home and system paths counts as a system commit.
- The lock shared with manual updates and the timer being ensured by `update` are decided and specified in `update-classification`.
- Safety net: after an unattended update the job runs the zsh handoff health check. If zsh no longer starts cleanly, it resets the checkout to the previous revision, re-applies chezmoi, does not retry that revision (until a manual `machine update` succeeds) and sets needs-attention with the reason.
- Timer units stay unchanged (every 6 hours, no `Persistent=true`), and the same job runs on every profile that has the timer, including `container` and `rpi-zero`.
- Not decided as wanted: running Ansible automatically even when sudo is passwordless (the owner chose the narrower scope).

## Considered and rejected

- Notify only, as today: rejected, the update should happen without the user.
- Automatic Ansible with passwordless sudo: not chosen for now.

## Open Questions

- Behaviour on battery, metered networks and when offline.
- A home-only commit that depends on a tool installed by a later system commit cannot be detected automatically; commit order is the only protection.
