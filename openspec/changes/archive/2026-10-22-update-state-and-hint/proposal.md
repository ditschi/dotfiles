## Why

Shell startup must stay fast, so updates happen in the background and the shell only reads a small state. Today the shell prints one generic line when a marker file exists; it says nothing about why or what to do, and it cannot tell that a shell predates an update that was already applied. A visible indicator in the prompt, similar to the git branch or virtualenv info, shows when a refresh of the shell is needed, when an update is pending, and when manual checking is needed.

## What Changes

- The background job writes a state with one of: nothing, update available, updated (reload the shell), needs attention (with a reason).
- zsh and bash show the state as a persistent prompt segment. A shell that was started after the update shows nothing.
- A one-line message at shell start only for needs-attention.
- The generic "update available" line at shell start is dropped.
- `machine status` explains the state and the fix.

## Capabilities

### Modified Capabilities
- `update-flow`: "Update hint at shell start" is replaced by the state indicator.

Profiles: all with an interactive shell. `rpi-zero` and `container` skip the prompt configuration files, so how they show the indicator is an open question.

## Impact

`home/dot_zshrc`, `home/dot_bashrc`, `home/dot_zsh/config/03_theme.zsh`, `home/dot_p10k.zsh`, `home/dot_config/starship.toml`, `home/dot_local/bin/executable_dotfiles-update-check-job`, `home/dot_local/lib/machine_cli/commands.py` (`cmd_status`), `tests/unit`.

Depends on `update-classification` (the reasons and areas it reports).
