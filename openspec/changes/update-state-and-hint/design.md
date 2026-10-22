## Context

The update-check timer runs `dotfiles-update-check-job` every 6 hours; it fetches and creates or removes `~/.dotfiles-update-available`. `home/dot_zshrc` and `home/dot_bashrc` print a fixed hint when the file exists. zsh uses Powerlevel10k, bash uses Starship when installed.

## Decisions

- The indicator is a persistent prompt segment in both shells, not text printed at startup.
- Four states: update available (low urgency), updated and reload needed (informational, ends when a new shell starts), needs attention with a reason (high urgency), nothing.
- A one-line message at shell start only for needs-attention. The generic startup hint is dropped.
- The segment is short; the reason and the fix are shown by `machine status`.
- Aligning zsh and bash on Starship is not a prerequisite and is not part of this change.
- A live shell is not reloaded automatically.
- Wanted, but only if it stays fast and lightweight: the segment is re-evaluated after each command, so an open shell shows state changes without a reload. If this cannot be done cheaply, the segment falls back to being evaluated at shell start only.

## Considered and rejected

- Startup text only: scrolls away in long-lived terminals and does not clear itself.
- Aligning on Starship first: not needed for the hint; deferred.

## Open Questions

- Cheap per-prompt refresh (unconfirmed): a `precmd` hook (zsh) and `PROMPT_COMMAND` (bash) compare the state file's modification time with the last seen one, without forking, and re-read it only when it changed. The cost per prompt must be measured against a budget before this is kept.
- Proposed mechanism (unconfirmed): the job writes a small state file; each shell remembers the revision it loaded and compares it to the applied revision with a file test, without forking. zsh renders a p10k function segment; bash sets one variable in `PROMPT_COMMAND` that a Starship `env_var` module shows.
- Segment texts and glyphs, and a `reload` alias (`exec zsh -l`) as the fix for reload-needed.
- Where the segment goes for `rpi-zero` and `container`, which skip the prompt configuration files, and for bash without Starship.
- Whether printing at startup interacts badly with the p10k instant prompt (console-output warning).
- Whether needs-attention that stays unresolved should escalate (for example a reminder after some days).
- Desktop notifications on laptops: not wanted at first; revisit if the segment is missed.
