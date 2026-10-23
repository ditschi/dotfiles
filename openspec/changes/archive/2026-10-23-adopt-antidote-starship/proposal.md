## Why

zinit is hard to configure, and the plugin set is a collection gathered over time that has not been maintained since. Bash and zsh also differ widely today. The spike `investigate-shell-plugin-manager` compared zinit, antidote and sheldon with a rebuilt plugin set, and the owner decided on 2026-10-23 to move to antidote with zsh-defer, Starship for both shells, the bash fallback level and delta. On this host the rebuilt setup shows the prompt after about 23 ms instead of 508 ms and is fully loaded after about 99 ms instead of 947 ms. Powerlevel10k is in limited-support mode upstream.

## What Changes

- **BREAKING** zinit is replaced by antidote. Deferred plugins load through zsh-defer with `-dmpr`. antidote installs itself and the plugins on the first zsh start. The old zinit data stays on disk, and a documented command removes it.
- **BREAKING** The plugin set is rebuilt in a fixed load order: zsh-completions, LS_COLORS, fzf-tab, zsh-history-substring-search, zsh-autosuggestions, fast-syntax-highlighting, plus git-open, git-recent and git-recall as commands on `PATH`.
  - zoxide replaces z.lua and zsh-z.
  - undollar and zsh-sudo become a few lines in the shared config.
  - zsh-syntax-highlighting is dropped.
  - eza, fd and diff-so-fancy are no longer fetched by the plugin manager. The tools come from mise (`adopt-mise`).
- `compinit` runs once in the deferred part, through ez-compinit (antidote author's plugin), with a cached dump. Its `compdef` queue lets modules such as the `machine` completion load in the normal order. `setopt correct` replaces the ineffective `ENABLE_CORRECTION`.
- **BREAKING** Powerlevel10k is removed (`~/.p10k.zsh`, the instant prompt, the p10k segments and the MesloLGS font download). Starship draws the prompt in zsh and bash from one `starship.toml`:
  - The current layout stays (directory, Git, update segment, status, Python, duration, time).
  - The prompt character `❯` is drawn by the `shell` module: green in zsh, purple in bash.
  - 🐳 marks a container.
  - Failed commands show in the status segment.
- `starship.toml` is linked on every profile, including `rpi-zero` and `container`.
- bash gets the fallback level:
  - Starship, `fzf --bash`, zoxide and LS_COLORS from the zsh plugin checkout
  - git-open, git-recent and git-recall on `PATH`
  - Up/Down prefix history search and Esc Esc sudo
  - the `❯` paste function
  - The distribution fzf path search, z.lua and the hand-written `PS1` code are removed. ble.sh is not used.
- The shell health check gets the antidote equivalent of today's zinit checks:
  - a fresh host is one without antidote or its generated plugin file;
  - the trial start also runs the deferred part, so a broken deferred plugin is detected.
- The Git pager switches from diff-so-fancy to delta, with a plain `less` fallback when delta is missing.
- `adopt-mise` is narrowed. It installs the shell tools (and adds delta), and drops ble.sh; this change owns the shell-config edits that `adopt-mise` had planned in tasks 1.3 and 1.7.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `zsh-plugins`: the plugin manager becomes antidote with zsh-defer, the plugin set is replaced, and the time-to-prompt and fully-loaded behaviour are specified.
- `shell-prompt`: Powerlevel10k is replaced by Starship in zsh. One shared configuration gives a per-shell prompt-character colour and a container marker, on every profile.
- `bash-shared-config`: bash gets the fallback level (fzf, zoxide, LS_COLORS, key bindings, Git helper commands, paste support).
- `shell-handoff`: the fresh-host requirement names antidote instead of zinit, and the trial start includes the deferred plugins.
- `git-config`: the shared defaults name delta instead of diff-so-fancy.

## Impact

- Profiles: all six (`work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`). `rpi-zero` and `container` now get `starship.toml`.
- Shell files: `home/dot_zshrc`, new `home/dot_zshenv`, new antidote plugin list, and these modules in `home/dot_zsh/config/`: `02_plugins.zsh`, `03_theme.zsh`, `04_keybindings.zsh`, `07_machine.zsh`.
- Bash and prompt files: `home/dot_bashrc` and `home/dot_config/starship.toml`.
- Handoff check: `home/dot_zsh/zsh-handoff-check.sh`.
- Files removed: `home/dot_p10k.zsh`. `home/.chezmoiignore` and `home/.chezmoiremove` change.
- Git config and container tooling:
  - `home/dot_gitconfig`: the pager
  - `home/dot_local/bin/executable_sde`: cache mount `zinit` → antidote
- Ansible: `ansible/roles/user_tools` (the MesloLGS download).
- Tests:
  - `tests/unit/test_zsh_handoff.py`
  - `tests/integration/test_profile_containers.py`: zinit stub and p10k assertions
  - `tests/integration/test_host_yaml_install.py`
- Docs: `Readme.md` (prompt segment, cleanup command).
- Other changes:
  - `adopt-mise`: tasks 1.2, 1.3, 1.7 and 1.8, and design.md are amended. That change's group 2 later moves the files named here.
  - `investigate-shell-layout`: the zinit `atinit` double load of `07_machine.zsh` goes away, and the loader gains a deferred part.
- Dependencies: antidote and zsh-defer (Git clones on the first start); delta, fzf, zoxide, eza, fd and starship from mise. Each tool is optional at runtime.
