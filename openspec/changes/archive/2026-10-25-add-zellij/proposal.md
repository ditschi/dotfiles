# Proposal

## Why

The owner wants a terminal multiplexer they can actually work with. tmux feels unfamiliar and complicated to them; zellij is much more intuitive, mainly because of its simple key bindings with the on-screen hint bar. zellij should therefore be available on every host, installed for the user only, like the other shell tools.

## What Changes

- zellij is installed by mise as a user-space tool (`aqua:zellij-org/zellij`) on every host, next to tmux in the core shell fragment, and pinned in `mise.lock` for linux-x64 and linux-arm64.
- zellij runs with its default key bindings (Ctrl+G locks and unlocks; while locked, keys such as Ctrl+T reach the shell, for example the fzf file search). No key is remapped, and fzf keeps Ctrl+T.
- Text selected with the mouse inside zellij, without Shift, goes to the primary selection, so a middle click pastes it (for example a cleanup command that apt prints). zellij gets a small config file that sets a copy script for this; the default OSC 52 copy does not reach the clipboard in GNOME Terminal and Ptyxis.
- Shells do not start zellij automatically. The owner starts it by hand with `zellij`.
- tmux stays installed and unchanged.

## Capabilities

### New Capabilities
- `terminal-multiplexer`: which terminal multiplexers every host gets, how they are installed and configured, and that shells do not start one automatically.

### Modified Capabilities
- None. `user-tools` already requires shell tools to come from mise without root; zellij is one more tool under that rule.

Affected profiles: all (`work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`), because the tool is in the `core` group. No root is needed.

## Impact

- `home/core/.config/mise/conf.d/10-shell.toml`, `home/core/.config/mise/mise.lock`.
- `home/core/.config/zellij/config.kdl`, `home/core/.local/bin/zellij-copy`, `tests/unit/test_zellij.py`. An existing `~/.config/zellij/config.kdl` is moved to `config.kdl.pre-dotfiles` when the dotfiles are applied.
- Readme (shell section): zellij is available, how to start it, Ctrl+G to lock.
- No change to `machine_cli`, Ansible, the shell start files or the host profiles.
