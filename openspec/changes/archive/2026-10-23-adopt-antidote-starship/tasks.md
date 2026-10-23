# Tasks

## 1. Coordination with adopt-mise

- [x] 1.1 Amend `openspec/changes/adopt-mise/tasks.md`:
  - 1.2: add `delta` and `tealdeer` to the tool fragments and remove `diff-so-fancy`.
  - 1.3: replace with a pointer to `adopt-antidote-starship`.
  - 1.7: drop ble.sh and the `dot_bashrc` edits, keeping the font steps.
  - 1.8: replace the zinit cache mount with the antidote one.

  Update the ble.sh line in `openspec/changes/adopt-mise/design.md`. Verify that `openspec validate adopt-mise` passes and that `grep -n "ble.sh\|zinit" openspec/changes/adopt-mise/tasks.md` shows no plan left that contradicts this change.

## 2. zsh plugins with antidote

- [x] 2.1 Add `home/dot_zshenv` with `skip_global_compinit=1`. Add `home/dot_zsh/plugins.txt` with the plugin order from design.md:
  - zsh-defer
  - ez-compinit
  - zsh-completions `kind:fpath`
  - LS_COLORS `kind:clone`
  - git-open, git-recent and git-recall `kind:path`
  - fzf-tab, history-substring-search, zsh-autosuggestions and fast-syntax-highlighting, each `kind:defer`, with their `pre:`/`post:` hooks

  Verify that `chezmoi apply --dry-run` (or `chezmoi diff`) shows both new links.
- [x] 2.2 Rewrite `home/dot_zsh/config/02_plugins.zsh`:
  - bootstrap antidote into `$ANTIDOTE_HOME/mattmc3/antidote` (XDG data dir, friendly names);
  - set `defer-options '-dmpr'`;
  - build `${XDG_CACHE_HOME:-~/.cache}/zsh/plugins.zsh` from `~/.zsh/plugins.txt` with `antidote bundle` when the list is newer, then source it;
  - add the `dotfiles_cache_eval` helper;
  - keep the fzf-tab and completion zstyles (`menu no`, `ftb-tmux-popup`, the eza/`ls` preview);
  - remove every zinit/zplugin call, the distribution fzf search, z.lua, zsh-z, eza/fd/diff-so-fancy programs and zsh-syntax-highlighting.

  Verify:
  - In a container with network, `TERM=xterm zsh -i -c exit` installs the plugins and writes nothing to stderr.
  - A second start does not fetch anything (run it with `--network none`).
- [x] 2.3 Set up compinit through ez-compinit:
  - turn on `use-cache` and turn `compstyle` off;
  - remove its prompt hook in `02_plugins.zsh`;
  - call `run-compinit` from the deferred init step (fzf-tab `pre:` hook) before `fzf --zsh` and `zoxide init zsh`;
  - remove the second `compinit` from `home/dot_zshrc`;
  - keep `fpath+=~/.zfunc` before the loader.

  Verify:
  - In an interactive zsh after loading, `machine <Tab>` offers subcommands. `07_machine.zsh` is sourced once: add a temporary counter, or use `zsh -x` and grep for it.
  - `zsh-bench` shows no `compinit` before the first prompt.
- [x] 2.4 Move the helpers into `home/dot_zsh/config/04_keybindings.zsh`:
  - `alias \$=''` and the `❯` function;
  - the sudo widget on Esc Esc;
  - the autosuggestion keys (Ctrl+Space, Ctrl+_) through the `post:` hook;
  - the Up/Down binding through the history-substring-search `post:` hook (the fallback binding stays).

  Then:
  - In `home/dot_zshrc`, replace `ENABLE_CORRECTION` with `setopt correct`, and remove the p10k instant prompt, the zinit installer and the duplicate `menu select`.
  - Set `DOTFILES_ZSH_DEFERRED_LOADED=1` in the fast-syntax-highlighting `post:` hook.

  Verify interactively in a container:
  - `$ echo hi`, `❯ echo hi`, Esc Esc, Up substring search, autosuggestion accept and `gti status` correction work.
  - `print $DOTFILES_ZSH_DEFERRED_LOADED` prints `1` after loading.
- [x] 2.5 Replace the zinit cache mount in `home/dot_local/bin/executable_sde` (and `sdx`, if it mounts one) with a persistent `~/.local/share/antidote` mount. Verify that a second `sde` start does not clone the plugins again.
- [x] 2.6 Replace `ZINIT_STUB` in `tests/integration/test_profile_containers.py` with an antidote stub, or a pre-seeded `ANTIDOTE_HOME`, so the test needs no GitHub access. Verify that `pytest tests/integration/test_profile_containers.py -m docker -k shells_start_cleanly` passes for all profiles.

## 3. Starship prompt in both shells

- [x] 3.1 Edit `home/dot_config/starship.toml`:
  - change the second line to `$container$shell`;
  - add the `shell` module (`❯` bold green for zsh, bold purple for bash, bold yellow for others);
  - add the `container` module (🐳);
  - disable `character`;
  - keep the rest of the current layout.

  Verify with `spike/prompt-capture.sh`, or the same `starship prompt` calls in a container, for zsh and bash, inside and outside a container, and after a failing command.
- [x] 3.2 Rewrite `home/dot_zsh/config/03_theme.zsh`:
  - cached `starship init zsh --print-full-init` when Starship is installed;
  - export `DOTFILES_UPDATE_SEGMENT` from a `precmd` hook;
  - without Starship, a built-in `PROMPT` (directory and green `❯`) plus the existing `RPROMPT` update function;
  - remove the p10k segments and the p10k load;
  - keep the autosuggestion highlight style.

  Verify:
  - With `~/.dotfiles-update-state` set to `available`, the zsh prompt shows the update segment, with and without Starship on `PATH`.
- [x] 3.3 Clean up the Powerlevel10k files and update the tests:
  - Delete `home/dot_p10k.zsh`.
  - Remove the `.p10k.zsh` and `.config/starship.toml` entries from `home/.chezmoiignore`.
  - Add `.p10k.zsh` to `home/.chezmoiremove`.
  - Remove the MesloLGS check and download tasks from `ansible/roles/user_tools/tasks/main.yml`.
  - Update `tests/integration/test_profile_containers.py` (no p10k link, `starship.toml` on every profile) and `tests/integration/test_host_yaml_install.py`.

  Verify:
  - `ansible-lint ansible/*.yml` passes.
  - The Docker profile tests pass.
  - On a host that had the link, `chezmoi apply` removes `~/.p10k.zsh`.

## 4. Handoff health check

- [x] 4.1 Update `home/dot_zsh/zsh-handoff-check.sh` as follows.
  - **Fresh host:** antidote (`$ANTIDOTE_HOME/mattmc3/antidote`) or the generated plugin file is missing. A host with old zinit data only is also fresh.
  - **Staleness check:** watch `~/.zsh/plugins.txt`, and stop watching `~/.p10k.zsh`.
  - **Trial start:** runs with `DOTFILES_ZSH_CHECK=1` and requires both `DOTFILES_ZSH_LOADED=1` and `DOTFILES_ZSH_DEFERRED_LOADED=1`.
  - **Check mode in `02_plugins.zsh`:** a `post:` hook on zsh-defer makes `zsh-defer` queue its command, and `00_LOADER.zsh` runs the queue at its end.
- [x] 4.2 Update `tests/unit/test_zsh_handoff.py`.
  - Change the fixture from the zinit dir to the antidote dir plus the generated file, and rename the fresh-host test.
  - Add a test for "only zinit data → fresh".
  - Add a test for "deferred plugin fails → cached failure, incomplete load".
  - Add a test for "plugin list edited → re-check".

  Verify that `pytest tests/unit/test_zsh_handoff.py -q` passes.

## 5. bash fallback level

- [x] 5.1 Rewrite the interactive part of `home/dot_bashrc` after the handoff block.
  - **Remove:**
    - the distribution fzf search
    - the z.lua block
    - both `PS1` assignments, `parse_git_branch` and `git-sh-prompt`
  - **Add:**
    - the cached helper for `starship init bash --print-full-init`, `fzf --bash` and `zoxide init bash`
    - LS_COLORS through `dircolors` from the antidote checkout (before the existing `di=0;32` override)
    - the git-open, git-recent and git-recall checkouts on `PATH`
    - readline Up/Down `history-search-*` and Esc Esc sudo
    - the `❯` function and `command_not_found_handle` for `$`
    - a plain `PS1` with the update prefix when Starship is missing
  - **Keep:**
    - the shared modules
    - the update state
    - the `machine` completion
    - NVM
    - `~/.bashrc-local`

  Verify:
  - In a container, `bash -i` starts without stderr on a host with the tools and on a host without them.
  - Ctrl+R opens fzf, `z` works, `git recent` is found, and `❯ echo hi` and `$ echo hi` work.
  - `spike/bash/bench-bash.sh` (or hyperfine) shows the first prompt in under 70 ms on the host.
- [x] 5.2 Extend `test_shells_start_cleanly` in `tests/integration/test_profile_containers.py`: in bash, assert that `STARSHIP_SHELL=bash` when Starship is installed, and that there are no errors without the tools. Verify that the Docker test passes.

## 6. delta as Git pager

- [x] 6.1 In `home/dot_gitconfig`:
  - change `core.pager` to the delta / `less -FXRi` / `cat` guard;
  - add `interactive.diffFilter` with the same guard (`delta --color-only`, otherwise `cat`);
  - add `[delta] navigate = true`.

  Verify that `git show` uses delta when it is installed and `less` when `PATH` has no delta, and that `git add -p` works in both cases. Run the git-config checks in `pytest tests/unit -q`.

## 7. Documentation

- [x] 7.1 Update `Readme.md`:
  - the prompt paragraph: Starship for both shells, with the update segment shown by the `env_var` module;
  - the plugin manager, antidote, and how to edit `~/.zsh/plugins.txt`;
  - a cleanup command for old data (`rm -rf ~/.local/share/zinit ~/.cache/p10k-* ~/.cache/gitstatus`).

  Remove the zinit comment from `04_keybindings.zsh` and remove `zshplugins`/`zshtheme` aliases that point at stale files. Verify `grep -rn "zinit\|p10k\|powerlevel\|diff-so-fancy\|z\.lua" home Readme.md ansible tests` finds only the `.chezmoiremove` entry and intended migration notes.
- [x] 7.2 Record a Purpose update for `openspec/specs/shell-prompt/spec.md` (Powerlevel10k → Starship in both shells) and for `zsh-plugins` (antidote). Apply it when this change is archived. Verify that `openspec validate adopt-antidote-starship --strict` passes.

## 8. Integration checks

- [x] 8.1 Measure the final configuration with the spike harness (`spike/bench.sh` with the repository's `home/` linked, or zsh-bench on the owner's workstation). Verify that the zsh first prompt is under 50 ms, zsh fully loaded is under 300 ms and the bash first prompt is under 70 ms. Record the numbers in design.md.
- [x] 8.2 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `ansible-lint ansible/*.yml`, and verify that all pass.

## Workflow follow-up

- After review, archive the change with `/opsx-archive`. This syncs the delta specs and applies the Purpose updates from task 7.2.
