# Design

## Context

Shell tools come from mise fragments under `home/core/.config/mise/conf.d/`; `10-shell.toml` already holds tmux (`aqua:tmux/tmux-builds`). The `core` group is applied on every profile, and `mise.lock` pins versions for linux-x64 and linux-arm64 only. The mise registry maps `zellij` to `aqua:zellij-org/zellij`, which ships static musl builds for both platforms. Ansible installs no tmux or zellij package, so the repository check against a second installation source is not affected. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- zellij is available by name in every interactive shell on every host.

**Non-Goals:**
- Starting zellij automatically, per host or globally.
- Remapping zellij or fzf keys.
- Replacing or removing tmux.

## Decisions

- **Installed on every host through the `core` group (owner request).** zellij goes into `10-shell.toml` next to tmux instead of a new feature or dotfile group, so no host needs to select it and no `machine_cli` code changes.
- **Short registry name `zellij`.** The registry resolves it to `aqua:zellij-org/zellij`, the same backend family as tmux; the aqua backend verifies checksums from the lockfile.
- **Default key bindings (owner decision).** The owner chose zellij largely for its simple key bindings. The default preset takes Ctrl+T, which fzf uses for its file search; the owner rarely uses it and reaches it through Ctrl+G (lock), Ctrl+T, Ctrl+G. An extra Alt+T binding for the fzf file search was offered and declined.
- **Mouse selection to the primary selection (owner request).** The owner copies a line of earlier output (for example a cleanup command that apt prints) and pastes it with a middle click. zellij copies a selection on release by default, but through OSC 52 to the clipboard, which GNOME Terminal and Ptyxis (VTE 0.84) ignore; a test showed neither selection changed. With `copy_command "wl-copy --primary"` the owner confirmed it works. The config sets `copy_command "zellij-copy"`, a small script in `~/.local/bin` that uses `wl-copy --primary` on Wayland, `xclip`/`xsel` on X11, and otherwise drops the text, so one config serves every host. Alternative not taken: `copy_clipboard "primary"` with the default OSC 52, because the terminal ignores OSC 52 anyway.
- **No automatic start (owner decision).** Shells stay plain and zellij is started by hand. An autostart was analysed and not taken: a feature `zellij-autostart` (local terminals and/or SSH logins) selected per host in `machine/hosts/<host>.yml`, with `machine` writing a marker file that zsh checks on start and `ZELLIJ_AUTOSTART=0/1` as a per-session override. The analysis also listed what such an autostart would have to handle: the bash-to-zsh health check (`zsh -l -i -c` with `DOTFILES_ZSH_CHECK=1`), shells without a TTY, IDE terminals and Guake, containers, zellij nested in zellij over SSH, sessions left running in the background, a different scroll and copy behaviour, and limited image preview in yazi. It is kept here as the starting point if autostart is wanted later.

## Risks / Trade-offs

- [Default bindings capture keys that programs in a pane use, e.g. Ctrl+O (save in nano, verbose view in Claude Code), Ctrl+T, Ctrl+G, Ctrl+S, Ctrl+P/Ctrl+N] → Ctrl+G locks zellij so the keys reach the program; a single key can be moved later in a config file if it disturbs daily use.
- [A copy command replaces zellij's OSC 52 copy, so over SSH a selection inside zellij no longer reaches the local clipboard, even in terminals that support OSC 52] → Shift + mouse still selects with the local terminal; this matches the behaviour before, since the owner's terminals ignore OSC 52.
- [`wl-copy` keeps a background process to serve the selection until something else is selected] → normal for Wayland clipboards.
- [A new zellij release is not picked up automatically] → as with every mise tool, a lockfile update commit brings the new version.

## Assumptions

- The zellij config file sets only what differs from zellij's defaults; key bindings stay at the defaults (no `keybinds` block).
