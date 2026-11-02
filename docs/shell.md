# Shell

zsh and bash configuration, prompt, plugins, completion and the terminal multiplexer.

`~/.zshrc-local` is only for genuine single-host exceptions and is not in git.

## Prompt and plugins

Both shells use [Starship](https://starship.rs) with the shared `~/.config/starship.toml` (every host). The prompt character shows the shell: a green `❯` in zsh, a purple `❯` in bash; `🐳` marks a container, and a failed command shows in the status segment. Without Starship both shells fall back to a plain prompt (directory and `❯`).

Shell configuration is under `~/.shell/{common,bash,zsh}`; each shell has an explicit ordered loader, and work-only files live in the separately selected work dotfile group at `~/.shell/work/{common,zsh}`. Shared `.sh` files must run in both Bash and zsh; Readline and ZLE integrations stay shell-specific. `.bashrc` performs the handoff before loading the Bash fallback, while `.zshrc` starts the explicit zsh loader. `~/.bashrc-local` and `~/.zshrc-local` remain host-only final extension points.

`~/.shell/common` owns aliases, env-file loading, machine profile, update/cache helpers and command-prefix matching. `~/.shell/bash/init.bash` explicitly loads the Bash handoff support, options, tools, shared environment/aliases, history, guarded work modules, Readline bindings and prompt. `~/.shell/zsh/init.zsh` loads profile and shared helpers, zsh options/tools and environment, guarded work modules, history, plugins, prompt and keybindings; machine completion is registered after deferred or fallback `compinit`. Adding a module does not load it until its shell loader names it.

`machine update` or `machine apply` applies the selected shell links. To roll back a layout change, restore the previous repository revision and run `machine update` so the managed links are reapplied; keep local override files and plugin/cache data in place.

zsh plugins are managed by [antidote](https://antidote.sh): edit `~/.shell/zsh/plugins.txt` (one plugin per line; order matters) and open a new shell — the generated `~/.cache/zsh/plugins.zsh` is rebuilt and missing plugins are cloned to `~/.local/share/antidote`. `antidote update` updates them. The prompt appears first; completion (`compinit`), machine completion, fzf-tab, history-substring-search, autosuggestions and fast-syntax-highlighting load in their declared deferred order via zsh-defer. Tools such as fzf, zoxide, eza, fd, delta and Starship come from mise; their shell init is cached in `~/.cache/zsh` and regenerated when the binary changes.

bash is a fallback with the same tools: Starship, fzf (Ctrl+R), zoxide (`z`), LS_COLORS and the git helpers (`git open`, `git recent`, `git recall`) from the antidote checkouts, Up/Down prefix search, Esc Esc for `sudo`, and pasting commands with a leading `$ ` or `❯ `.

### Command completion

Native Bash and Zsh completion generators are available for Copilot CLI, Zellij, GitHub CLI, OpenCode, uv, mise, lazygit, OpenSpec, Starship and Git LFS. Bash registrations live in `~/.shell/bash/tools.bash`; Zsh registrations live in `~/.shell/zsh/plugins.zsh` and run after `compinit`, before `fzf-tab`. Both use `~/.shell/common/cache-eval.sh` to cache generated scripts under `~/.cache/zsh` and refresh them when the executable changes. The native Bash completions for GitHub CLI and Git LFS are loaded only when `bash-completion` provides their required helper. fzf and zoxide already include completion in their shell initialization, and `machine` has its own generated completion.

The system Bash and Zsh completion providers also supply common commands such as Git, jq and npm; provider coverage varies by host. The current Bash provider additionally covers gh, eza and Yazi, while the current Zsh provider covers tmux. Upstream static completions not supplied by the configured providers are not bundled by this change: eza (Zsh), fd (Zsh; its Bash file is for the `fdfind` alias), delta (Bash and Zsh) and tealdeer (Bash and Zsh). No native completion generator was found for Claude Code, `gext`, Node.js, Yazi or the Thunderbird CLI/bridge.

Data of the former zinit/Powerlevel10k setup is not removed automatically. After the switch it can be deleted with:

```bash
rm -rf ~/.local/share/zinit ~/.cache/p10k-* ~/.cache/gitstatus
```

Before bash hands over to zsh, a startup health check runs. If zsh fails or loads only partly, the shell stays in bash and prints one line with the reason. The result is cached until a shared or zsh module, work startup file, plugin list, entry point, health checker, zsh binary or `~/.preferred-shell` changes, or dotfiles are updated. After fixing the cause, run `zsh-recheck` to clear the cache and check again.

The trial zsh runs in its own session without the terminal, so nothing it starts can read your input; a timeout (60 s, `DOTFILES_ZSH_CHECK_TIMEOUT`) or Ctrl-C ends it and everything it started, and the shell stays in bash without caching the result. If a login still hangs, connect with a shell that reads no startup files and fix it from there:

```sh
ssh -t <host> 'bash --noprofile --norc -i'
```

## Terminal multiplexer

[zellij](https://zellij.dev) is installed on every host (mise, `10-shell.toml`) and runs with its default key bindings; the bar at the bottom shows the available keys. Start it by hand with `zellij`; shells never start it automatically. Ctrl+G locks zellij so that every key goes to the program in the pane (for example Ctrl+T for the fzf file search, or Ctrl+O in nano), and Ctrl+G unlocks it again. Text selected with the mouse inside zellij (no Shift needed) goes to the primary selection, so a middle click pastes it; `~/.config/zellij/config.kdl` sets `copy-selection` (`wl-copy --primary` on Wayland, `xclip`/`xsel` on X11) because GNOME Terminal and Ptyxis ignore zellij's default OSC 52 copy. Without a graphical session (SSH) the selection is not copied; Shift + mouse selects with the terminal as before. tmux stays available with `~/.tmux.conf`.
