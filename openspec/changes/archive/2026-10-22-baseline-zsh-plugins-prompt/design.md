# Design

## Context

This change writes the confirmed zsh plugin and prompt behaviour down as baseline specs and changes no code. The behaviour lives in `~/.zshrc`, `02_plugins.zsh`, `03_theme.zsh`, `~/.p10k.zsh` and the chezmoi ignore list. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Record only owner-confirmed behaviour as requirements.
- Keep every unconfirmed observation visible so it can be confirmed or investigated later.

**Non-Goals:**
- Fixes or improvements, including plugin removal.
- The zsh startup health check (already part of `shell-handoff`).

## Decisions

1. **zinit is the plugin manager.** The intention is a fast shell start: zinit installs itself automatically and loads plugins lazily where possible. Whether all lazy-loading options are used is an investigation.
2. **The Powerlevel10k look is kept.** The configuration is set up by hand once and not regenerated routinely.
3. **Starship in bash only if installed.** It is assumed to be installed by default on most profiles; this is not confirmed.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Plugin manager and lazy loading.** Suggestion: check whether every plugin that can be loaded lazily is, and compare zinit with antidote and sheldon on startup time. Why: a fast shell start is the goal, and it is not certain all lazy-loading options are used.
2. **Overlapping and unneeded plugins.** Much of the set was added because it was found and sounded nice. Suggestion: find out what zsh-z and z.lua actually do for the owner, whether one covers the other (and autojump), and whether both syntax-highlighting plugins add behaviour. Why: fewer plugins means a faster start and fewer dependencies.
3. **fzf structure.** fzf comes from the distro (apt, feature `zsh-full`) with key bindings and completion sourced only when found, probably correct but with no known reason beyond that it works. Suggestion: clean up and streamline how fzf is provided and loaded. Why: the structure has grown without a recorded reason.
4. **Skipped prompt profiles.** `.p10k.zsh` and `starship.toml` are not installed on `rpi-zero` and `container`. The owner is unsure why and does not confirm it as intended. Hypothesis (unconfirmed): in a container the installation would repeat in every new container and slow startup; no idea for `rpi-zero`. Suggestion: decide per profile whether the prompt should be installed. Why: a rule without a known reason may remove a wanted prompt.
5. **Syntax highlighting order.** The code loads zsh-syntax-highlighting last; whether that is required is unclear. Suggestion: verify against the plugin documentation and test. Why: a needless ordering constraint complicates changes to the plugin list.
6. **The prompt-mark stripping does not work.** The intention is that pasting a copied command with the prompt mark runs it without the mark (undollar extension). Removal currently does not work. Suggestion: investigate and fix as its own change. Why: the extension is there but gives no benefit.
7. **One prompt look.** Future alignment of the bash and zsh prompts may be reasonable if the Docker marker and the colour differentiation between the shells are kept. Suggestion: evaluate a shared setup. Why: two prompt setups double maintenance.

## Risks / Trade-offs

- The specs omit the skipped prompt profiles (investigation 4), but the current configuration still skips them; later changes must not change this silently.

## Open Questions

- Is Starship installed by default on most profiles? Assumed, not confirmed.
