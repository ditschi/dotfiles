# Design

## Context

Powerlevel10k's `context` segment showed `user@hostname` in the right prompt only over SSH or as root. The Starship configuration from `adopt-antidote-starship` kept the layout but has no counterpart, so the indicator disappeared in zsh; bash never had one.

## Decisions

- **Starship's `username` and `hostname` modules.** Starship detects SSH itself (`SSH_CONNECTION`, `SSH_CLIENT`, `SSH_TTY`), so the same configuration works in zsh and bash without shell hooks. `hostname` uses `ssh_only = true`; `username` shows by default only over SSH or as root.
- **Content like p10k:** `user@hostname` over SSH; in a local root shell only the user name.
- **Position:** first line, right part, directly in front of the time, matching p10k's right prompt.
- **Both modules are in one conditional group** `($username$hostname )`, so no stray space appears when neither is shown.
- **Colours like p10k:** 180 for users, bold 178 for root.

## Alternatives considered

- Hostname only over SSH: rejected by the owner in favour of the p10k behaviour.
- Placing it at the start of the first line: rejected by the owner; the indicator stays where p10k had it.
- Louder colours (bold yellow/red): rejected by the owner; the p10k colours are kept.

## Open Questions

- The plain fallback prompt (no Starship) does not show the indicator. Not requested in this change.
