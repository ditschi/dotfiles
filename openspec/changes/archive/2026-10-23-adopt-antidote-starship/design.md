# Design

## Context

The zsh setup today has these parts:
- **Startup:**
  - `.zshrc` sources the Powerlevel10k instant prompt.
  - It installs zinit itself.
  - It runs the loader (`00_LOADER.zsh` sources `config/*.zsh` in order).
  - It runs a second `compinit` at the end.
- **`02_plugins.zsh`:**
  - loads the plugins with zinit turbo;
  - fetches eza, fd, git-recent, git-recall and diff-so-fancy as zinit programs;
  - searches distribution paths for the fzf scripts;
  - sources `07_machine.zsh` from a zinit `atinit` hook. This is a second load, because `07_machine.zsh` returns early unless `compdef` exists.
- **Prompt:** `03_theme.zsh` loads Powerlevel10k with custom segments for Docker and the update state.
- **bash:** builds its own `PS1`, searches for fzf scripts and z.lua, and starts Starship last when it is installed.
- **Health check:** `zsh-handoff-check.sh` treats a host without `~/.local/share/zinit/zinit.git` as fresh. It checks `DOTFILES_ZSH_LOADED=1`, which the loader sets.

Measured on this host (spike `investigate-shell-plugin-manager`, Candidates table): the current setup shows the prompt after 508 ms and is fully loaded after 947 ms.

The spike rebuilt the feature set from scratch for antidote (`spike/configs/antidote/`, `spike/configs/_common/`, `spike/bash/`). This design ports that reference into `home/`. See proposal.md for the motivation and the specs for the required behaviour.

Constraints:
- chezmoi symlink mode: files in `$HOME` are links into the repository, so generated files must not be written next to linked files.
- Every profile must start without errors when a tool is missing.
- The `adopt-mise` change will later move `home/` into group directories.

## Goals / Non-Goals

**Goals:**
- Port the spike's antidote configuration with the same load order and zsh-defer options, so the measured times carry over.
- One cached helper for tool init output, shared by zsh and bash.
- Make the deferred part visible to the handoff health check.
- Keep the existing modules (`00_alias` … `08_node`), the loader order and the extension points (`~/.zshrc-local`, `~/.bashrc-local`).

**Non-Goals:**
- Installing tools. That belongs to `adopt-mise`; this change only uses tools that are present.
- Restructuring the module layout. That is `investigate-shell-layout`.
- ble.sh and atuin. The owner decided against both.
- Deleting old zinit or Powerlevel10k data on existing hosts.

## Decisions

### antidote with zsh-defer `-dmpr`, rather than sheldon or a rebuilt zinit

The owner chose antidote (investigation Decision 1).

Rejected alternatives, with the owner's reasons:
- **sheldon** is as fast. The owner would have preferred it only if one configuration could install the same plugins for bash and zsh. The spike showed that bash would use only LS_COLORS from such a file, so a shared file brings nothing. sheldon also has had no release for 15 months.
- **zinit, rebuilt** meets the targets but is slower (fully loaded after 161 ms instead of 99 ms, installed in 16 s instead of 6 s). zinit is also what the owner finds hard to configure.
- **Keeping the current setup** is about 10× slower.

zsh-defer runs with `-dmpr` (set through `zstyle ':antidote:bundle:*' defer-options '-dmpr'`). Its defaults run precmd hooks and redraw the prompt after every step, which cost +43 ms until fully loaded.

### Where antidote, the plugins and the generated file live

| Item | Path | Why there |
|---|---|---|
| Plugin list (in the repository) | `home/dot_zsh/plugins.txt` → `~/.zsh/plugins.txt` | one line per plugin |
| Plugin checkouts (`ANTIDOTE_HOME`) | `${XDG_DATA_HOME:-~/.local/share}/antidote`, friendly names (`owner/repo`) | data, not cache: a cache cleanup must not leave the generated file pointing at missing checkouts |
| antidote itself | `$ANTIDOTE_HOME/mattmc3/antidote` | updated like the plugins |
| Generated file | `${XDG_CACHE_HOME:-~/.cache}/zsh/plugins.zsh` (output of `antidote bundle`) | cheap to rebuild; next to the cached `machine` completion; never inside the repository |

The generated file is rebuilt when the plugin list is newer. The `sde` and `sdx` containers mount a persistent `antidote` directory instead of the `zinit` one.

### Load order: synchronous part, then one deferred chain

The synchronous part:
- `.zshenv`: `skip_global_compinit=1`
- `.zshrc`:
  - options: `setopt correct`, `bindkey -e`, `fpath+=~/.zfunc`
  - Starship init, cached
  - the loader

In the loader, `02_plugins.zsh` bootstraps antidote and sources the generated plugin file. It rebuilds that file with `antidote bundle` only when `plugins.txt` is newer, instead of calling `antidote load`. The bundle step sends the clone progress to stdout, so a first start writes nothing to stderr. It replaces the file only when the build succeeds, so an offline start keeps the previous file.

The plugin list keeps the spike order:
1. zsh-defer
2. mattmc3/ez-compinit. It replaces `compdef` with a queue until the real `compinit` runs; its prompt hook is removed (see "compinit through ez-compinit, deferred").
3. zsh-completions (`kind:fpath`)
4. LS_COLORS (`kind:clone`)
5. git-open, git-recent and git-recall (`kind:path`). They only extend `PATH`, so they cost nothing at startup. git-recall is not executable in its repository: a `post:` hook sets the executable bit once and sets `core.fileMode false` in that clone, so `antidote update` keeps pulling.
6. fzf-tab (deferred). Its `pre:` hook queues a deferred init step in front of it. The init step reads LS_COLORS from the cache, runs ez-compinit's `run-compinit` once (cached dump, which also replays the queued `compdef` calls), and sources `fzf --zsh` and `zoxide init zsh` (both cached).
7. history-substring-search (deferred; its `post:` hook binds Up and Down)
8. zsh-autosuggestions (deferred; its `post:` hook starts it and binds Ctrl+Space and Ctrl+_)
9. fast-syntax-highlighting (deferred; its `post:` hook sets the fully-loaded marker)

### compinit through ez-compinit, deferred

`compinit` is still required: it turns on the completion system that Tab completion, fzf-tab and every `compdef` call (`machine`, fzf, zoxide) depend on. antidote does not run it; it only adds plugin folders to `fpath`.

`mattmc3/ez-compinit` is maintained by antidote's author and does two things:
- it defines a placeholder `compdef` that queues the calls until the real `compinit` runs;
- it runs `compinit` from a cached dump when `zstyle ':plugin:ez-compinit' use-cache yes` is set.

Because of the placeholder, modules such as `07_machine.zsh` run once in the normal loader order, and their `compdef` calls are replayed after `compinit`. The double load disappears without a special list.

By default ez-compinit runs `compinit` in a prompt hook, before the first prompt. In the spike that cost about 17 ms. So `02_plugins.zsh` removes that hook (`add-zsh-hook -d precmd run-compinit`), and the deferred init step calls `run-compinit` itself. Its completion styles are turned off (`compstyle` set to `off`); the dotfiles keep their own zstyles.

Confirmed by the owner on 2026-10-23.

Rejected alternatives:
- **ez-compinit with its default prompt hook**: simpler, but about +17 ms to the prompt.
- **The spike's own helper plus a `dotfiles_after_compinit` list**: no extra plugin, but every module that needs `compdef` has to know about the list.

The second `compinit` at the end of `.zshrc` goes. So does the zinit `atinit` that sourced `07_machine.zsh`.

The undollar alias (`alias \$=''`), the `❯` function and the zsh-sudo widget (Esc Esc) move into `04_keybindings.zsh`. The fzf-tab and completion zstyles move into `02_plugins.zsh`. They follow the spike (`menu no`), and the current `ftb-tmux-popup` and `eza`/`ls` preview styles are kept.

Alternative considered: loading everything synchronously. The spike measured an 88 ms prompt for that, above the 50 ms target.

### One cached init helper

`dotfiles_cache_eval <name> <cmd…>` writes the output of a tool's init command to `${XDG_CACHE_HOME}/zsh/<name>.zsh` (`.bash` for bash) and sources it. It regenerates the file when the tool binary is newer than the file, and does nothing when the tool is missing.

It is used for starship, fzf and zoxide. `mise activate` stays as `adopt-mise` added it.

### Health check sees the deferred part

zsh-defer runs from the line editor, so `zsh -l -i -c …` in the health check never runs the deferred part. The fully-loaded marker therefore lives in a new variable, `DOTFILES_ZSH_DEFERRED_LOADED=1`. `DOTFILES_ZSH_LOADED` still means "loader done".

When `DOTFILES_ZSH_CHECK=1`, a `post:` hook on the zsh-defer bundle replaces `zsh-defer` with a function that queues its command; `00_LOADER.zsh` runs the queue after all config files are sourced (some hooks, such as `_history_substring_search_config`, are defined after `02_plugins.zsh`). The trial start then loads every plugin in the same order, and the check requires both markers.

A fresh host is one without `$ANTIDOTE_HOME/mattmc3/antidote` or without the generated file. The plugin list joins the files watched for cache invalidation.

Alternative considered: checking only the synchronous part. Rejected, because a broken deferred plugin would then pass the check and fail in every interactive shell.

### Starship in both shells from the current `starship.toml`

The owner kept the current layout: directory, Git, a fill line, update segment, status, Python, duration and time. In the second line, `$character` becomes `$container$shell`:
- The `shell` module draws `❯`: bold green in zsh, bold purple in bash, bold yellow in other shells.
- The `character` module is disabled, so errors show only in the status segment.
- The `container` module shows 🐳.

The file is linked on every profile, so `.chezmoiignore` drops both prompt entries.

The update segment stays the Starship `env_var` module. zsh exports `DOTFILES_UPDATE_SEGMENT` and refreshes it in a `precmd` hook, like bash does today in `PROMPT_COMMAND`.

Without Starship:
- zsh uses a built-in `PROMPT` (directory and a green `❯`) plus the existing `RPROMPT` update function;
- bash keeps a simple `PS1` with the update prefix.

The p10k Docker and update segments are removed.

Rejected alternative: Powerlevel10k. It draws the prompt sooner (7 ms) and costs less per command in Git repositories (9 ms instead of about 25 ms), but it is in limited-support mode, and it cannot serve bash.

### bash fallback level

`dot_bashrc` keeps the handoff block, the shared modules, the update state, the `machine` completion, NVM, `~/.bashrc-local` and the existing `di=0;32` LS_COLORS override.

It drops:
- the distribution fzf path search
- the z.lua block
- the two hand-written `PS1` assignments with `parse_git_branch`
- the git-sh-prompt sourcing

It adds, from `spike/bash/common.bash` and `fallback.bashrc`:
- the cached helper for starship, `fzf --bash` and zoxide
- LS_COLORS through `dircolors` from `$ANTIDOTE_HOME/trapd00r/LS_COLORS/LS_COLORS`
- the git helper checkouts on `PATH`
- readline bindings: Up/Down `history-search-*`, and Esc Esc prepends `sudo`
- the `❯` function
- a `command_not_found_handle` for `$`

Rejected alternatives:
- **ble.sh**: 303 ms to the first prompt, and no stable release.
- **atuin**: the owner keeps fzf Ctrl+R.

### delta as Git pager with a fallback

`core.pager` keeps today's `sh -c` guard and switches the binary: delta when installed, otherwise `less -FXRi`, otherwise `cat`. `interactive.diffFilter` uses the same guard with `delta --color-only`, otherwise `cat`, so `git add -p` keeps working without delta.

delta's defaults are used, with `navigate = true`.

Rejected alternative: diff-so-fancy. It is a Perl script fetched by zinit and has no syntax highlighting. The owner chose delta.

### Coordination with adopt-mise

The owner chose the split: this change owns every shell configuration edit, and `adopt-mise` only installs tools. The planning edits are part of this change:
- `adopt-mise` tasks.md:
  - 1.2 adds delta and drops diff-so-fancy.
  - 1.3 moves here.
  - 1.7 loses ble.sh and the `dot_bashrc` edits.
  - 1.8 mounts the antidote cache instead of the zinit cache.
- `adopt-mise` design.md: the ble.sh line is updated.

Because every tool is optional at runtime, neither change has to land first.

tealdeer (`tldr`) is wanted (owner, 2026-10-23). Like the other tools, it is installed through the `adopt-mise` tool fragments (task 1.2), because this change installs no tools.

## Measurements (task 8.1)

Measured on 2026-10-23 with the spike harness in the `shell-spike:local` container: the real `home/` files, `spike-marker.zsh` queued with `zsh-defer -dmpr` as the last step, and 10 warm runs after 3 warm-ups (median/p90 in ms). The method follows the spike: **prompt** is the time to the first `zle-line-init`, **loaded** is the time until the last deferred step has run, and **zb-prompt** is zsh-bench's `first_prompt_lag`, which includes Starship's `git_status`.

| Config | prompt | loaded | zb-prompt | command_lag | input_lag | first install |
|---|---|---|---|---|---|---|
| final zsh (this change) | 45.1/46.6 | 109.1/118.3 | 68.5/71.2 | 40.3/41.4 | 4.4/5.3 | 6612 |
| spike `antidote` (same run, for reference) | 18.8/20.9 | 91.9/97.3 | 39.4/43.2 | 30.3/31.9 | 4.4/5.4 | 3618 |
| final bash (`bash -i`, first prompt) | 61.9/63.6 | – | – | – | – | – |
| bash without `mise activate bash` | 42.0/45.1 | – | – | – | – | – |
| bash with the `mise activate` output cached | 59.1/65.1 | – | – | – | – | – |

- zsh meets both targets: prompt < 50 ms and loaded < 300 ms. Of the 26 ms above the spike config, `mise activate zsh` (from `adopt-mise`) takes about 15 ms: about 5 ms for the activate fork and 10 ms for `mise hook-env`. The rest is the real config files.
- bash meets its target of < 70 ms (61.9 ms, and 60.2 ms after the `PROMPT_COMMAND` fix below). The original target was < 50 ms. The owner raised it to < 70 ms on 2026-10-23, because bash is the fallback and the only easy fix, mise shims, would go against `adopt-mise`.
- mise costs the same in both shells: about 5 ms to generate the activate script and 10–15 ms to evaluate it, mostly `mise hook-env --force`. Caching the script does not help. bash is slower because its own base is higher: 42 ms without mise against about 30 ms for zsh, mostly from `fzf --bash` and bash-completion.
- Found while measuring: `dot_bashrc` set `PROMPT_COMMAND` after `mise activate bash`, which dropped mise's prompt hook, so tool and env changes (`mise use`, an edited `mise.toml`) appeared only after the next `cd`. bashrc now puts `_mise_hook_prompt_command` back in front. This was checked with a `mise.toml` `[env]` entry: before the fix the value was missing, after it the value is set.
- On the owner's workstation (host, `WORK_SETUP=true`), zsh-bench reports a zb-prompt of 92 ms. `01_work.zsh` (forks `whoami`, `id` and `tput`, about 30 ms) is not part of this change, and Starship's `PROMPT2` fork takes about 16 ms on this host.

## Risks / Trade-offs

- [Until `adopt-mise` installs the tools, a host may lack fd, zoxide, delta or Starship (Ansible installs Starship only for hosts with the `starship` feature)] → Every integration is guarded. The shell starts with the parts that are present; for example, the fzf-tab preview falls back to `ls`, and the prompt falls back to the built-in one. The README notes `mise use -g` for single tools.
- [Starship costs about 25 ms per command in large Git repositories] → Accepted by the owner. `git_status` can be disabled per repository through Starship's own options if needed.
- [First zsh start on a fresh host clones about 10 repositories, synchronously] → The handoff treats such a host as fresh. Without network, zsh still starts with the built-in key bindings.
- [The bash `$ cmd` paste runs in a subshell, so `$ cd dir` does not change the directory] → Documented in the spec. `❯ cmd` works fully.
- [`adopt-mise` group 2 renames `home/` files] → Whichever change lands second rebases its paths. The tasks name the files by their current paths.
- [The check-mode zsh-defer replacement could drift from the real deferred behaviour] → It runs the same commands in the same order, and a unit test with a failing deferred plugin covers it.
- [Old data stays on disk (`~/.local/share/zinit`, `~/.cache/p10k-*`, `~/.cache/gitstatus`)] → The Readme documents one cleanup command. The dangling `~/.p10k.zsh` link is removed through `.chezmoiremove`.

## Migration Plan

1. `machine update` (or `chezmoi apply`) links the new files and removes the `~/.p10k.zsh` link.
2. The next interactive zsh clones antidote and the plugins. The handoff check treats the host as fresh until the generated file exists.
3. Rollback: revert the commit and run `machine update`. zinit and the p10k caches are still on disk, so the old setup starts without new downloads.

## Assumptions

- `machine_cli/core.py` keeps `.p10k.zsh` in `OLD_ROOT_LINK_NAMES`. That list is used to migrate old root links, and keeping the name there is harmless.

## Open Questions

- Should delta use side-by-side or line numbers by default? This can be tuned in `dot_gitconfig` after the owner has used it.

## Purpose updates (apply when archiving)

Delta specs cannot change a spec's Purpose, so these are applied by hand when the change is archived:

- `openspec/specs/shell-prompt/spec.md`: "Defines the prompt of the interactive shells: Starship with one shared configuration in zsh and bash, which differ only in the colour of the prompt character, and a plain built-in prompt when Starship is missing."
- `openspec/specs/zsh-plugins/spec.md`: "Defines how zsh plugins and helper programs are managed with antidote, so that the prompt appears before the plugins load, the plugin set is installed without manual steps and the list stays easy to edit."
