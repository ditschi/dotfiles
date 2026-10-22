# Proposal

## Why

The zsh plugin and prompt setup is the second area moved from the temporary decision log into OpenSpec, so that later changes build on a written baseline instead of on history and guesswork.

Motivation confirmed by the owner:

- Startup performance matters. zinit was chosen after research described it as fast and flexible.
- The current Powerlevel10k look is enjoyed. Its configuration was set up by hand once and is not routinely regenerated.
- Bash uses Starship as its prompt when it is installed.
- The owner wants to review overlapping plugins and reduce dependencies where that loses no useful behaviour.

## What Changes

- Describe the confirmed behaviour as baseline requirements: zinit as the plugin manager, the configured plugin set, the Powerlevel10k prompt in zsh and Starship in bash.
- Points the owner marked unclear or doubtful (fzf structure, skipped prompt profiles, plugin order, the `❯` stripping) stay out of the specs and are investigations in design.md with a suggestion and its reason.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

Boundaries are a proposal and are settled together with the owner:

- `zsh-plugins`: how zsh plugins and tools are managed and loaded.
- `shell-prompt`: which prompt each shell shows.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations and the unconfirmed hypotheses.

## Impact

- Decision records: 0003-zsh-plugins-and-prompt (to be retired once its content lives in specs and design).
- Profiles: all.
- Code: none. This change only adds planning artifacts.
