# Tasks

## 1. Install zellij

- [x] 1.1 Add `zellij = "latest"` to `home/core/.config/mise/conf.d/10-shell.toml` next to tmux and regenerate the lockfile with `mise lock --global --platform linux-x64,linux-arm64`. Verify `mise.lock` has zellij entries for both platforms and `python3 -m machine_cli.mise_check` passes.
- [x] 1.2 Run `mise install` on this host. Verify `zellij --version` works in a new zsh and bash, Ctrl+G then Ctrl+T opens the fzf file search inside a zellij pane, and a new terminal window still starts a plain zsh.

## 2. Copy to the primary selection

- [x] 2.1 Add `home/core/.local/bin/zellij-copy` (wl-copy --primary on Wayland, xclip/xsel on X11, otherwise drop) and `home/core/.config/zellij/config.kdl` with `copy_command "zellij-copy"`. Verify `tests/unit/test_zellij.py` passes, `zellij --config home/core/.config/zellij/config.kdl setup --check` reports a well-defined file, and `echo x | zellij-copy; wl-paste --primary` prints `x`.
- [x] 2.2 Apply the dotfiles on this host and test in a new zellij session: select output without Shift, middle-click pastes it.

## 3. Docs and checks

- [x] 3.1 Add zellij to the user-space tool list in the Readme and add a short note in the shell section: start with `zellij`, Ctrl+G locks and unlocks so keys reach the program in the pane (e.g. Ctrl+T for fzf), mouse selection without Shift goes to the middle-click selection, tmux stays available. Verify the text matches the behaviour.
- [x] 3.2 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `openspec validate add-zellij --strict`. Verify all pass.
