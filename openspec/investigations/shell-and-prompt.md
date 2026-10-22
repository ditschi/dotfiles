# Investigation report: shell and prompt

Read-only research for the investigations in three archived changes: `2026-10-21-baseline-shell-setup`, `2026-10-22-add-zsh-startup-check` and `2026-10-22-baseline-zsh-plugins-prompt` (design.md of each). Nothing was changed in code. Decisions stay with the owner. "Verified" means checked by reading code or running a command here; "unverified" means not checked or only a hypothesis.

# A. baseline-shell-setup

## A1. Default handoff outside Docker and outside `bash -c`

**Findings**
- `home/dot_bashrc` has two handoff paths. A `~/.preferred-shell` that is not bash is honoured everywhere (also in Docker and when bash runs a command string). The default path (zsh when no preferred shell is set) runs only if `/.dockerenv` is absent and `$BASH_EXECUTION_STRING` is empty (verified).
- Git history: both guards were added in one commit, `eb566ce` ("Enhance auto-switching logic ... to support user-defined shell preferences and Docker environments"). The message names Docker but gives no reason for either guard. The `.bashrc` is already interactive-only (`case $-` at the top), and `bash -ic 'cmd'` sets `BASH_EXECUTION_STRING`, so the second guard only matters for interactive-with-command cases (verified from code).
- `sde`/`sdx` (Readme "Project Containers"): interactive sessions "prefer zsh, falling back to Bash". How that is done is in the launcher, not in `.bashrc`; whether it relies on the Docker guard is not verified.
- Nested and manually started shells are handled separately by the parent-shell and `SHLVL` check, so these two guards are not what protects them (verified).
- Reason for the Docker guard: unknown. Hypothesis (unconfirmed): in a container the default handoff would start zsh and trigger the zinit bootstrap in every new container (same hypothesis as in prompt investigation B4).

**Suggestion:** keep the guards for now and add the observation to the spec as "reason unknown". Test once with a devcontainer without `.preferred-shell`: if zsh is wanted there, drop the Docker guard from the default path only. Reason: removing it blindly could trigger a slow plugin bootstrap in throwaway containers; keeping it blindly may block a wanted zsh.

## A2. Handoff mechanism

**Findings**
- Current: `exec zsh -l` from `.bashrc`, with a parent-shell check, `SHLVL` check, `.preferred-shell`, Docker/`bash -c` guards and, since the startup-check change, the health check `home/dot_zsh/zsh-handoff-check.sh` (verified).
- `home/dot_profile` and `home/dot_zprofile` exist. Whether `.profile` handoff would cover the cases (terminal emulators that start non-login interactive bash read only `.bashrc`) is unverified.
- The company route (SSSD `override_shell`) is mentioned in the design, but nothing in the repo implements or documents it (verified by search); its availability on the work hosts is unverified.
- The guards do real work: tests in `tests/unit/test_zsh_handoff.py` cover the bashrc handoff, nested shells, and an unhealthy zsh staying in bash.

**Suggestion:** do not replace the mechanism. Only revisit if the owner can confirm `override_shell` works on work hosts; it would remove the need for `.bashrc` handoff there. Reason: the current approach is tested and working; an alternative is speculative without that confirmation.

## A3. Folder structure of the shell configuration

**Findings**
- `home/dot_zsh/config/` is flat: `00_alias`, `01_env`, `01_work*` (3 files), `02_plugins`, `03_theme`, `04_keybindings`, `05_pyenv`, `06_history`, `07_machine`, `08_node`, plus `00_LOADER.zsh` which sources all `*.zsh` by glob (verified).
- Work modules are excluded per profile in `home/.chezmoiignore` (not `work-machine`), so the work condition is already enforced by file presence (verified).
- `.zsh/config/01_env.zsh` is also loaded by `git-credential-env` via `bash -c` (see baseline-git-config report), so a folder move touches that caller too (verified from that report).
- The hard-coded bash module list: not re-verified here.

**Suggestion:** do not restructure now. If done later, do it as its own change that lists all consumers (`.bashrc`, `git-credential-env`, `zsh-handoff-check.sh` watch list, `.chezmoiignore`, tests). Reason: the watch list of the health check and the credential helper both depend on the current paths, so the cost is higher than the design suggests.

## A4. Module loading scheme

**Findings**
- Loading is by glob in alphabetical order (`00_LOADER.zsh`). Order dependencies visible in code: `02_plugins.zsh` sources `07_machine.zsh` from a zinit `atinit` hook (so 07 runs before the glob reaches it normally, and again via the glob — double load is possible, unverified), and `03_theme.zsh` must come after zinit setup in `.zshrc` (verified).
- Two modules share the number 01 and 00, so number ties already rely on alphabetical order.

**Suggestion:** keep numbering. Check once whether `07_machine.zsh` is sourced twice and, if so, guard it. Reason: this is a concrete issue the explicit-list idea would also expose; the rest is cosmetic.

## A5. `chsh` on work hosts

**Findings**
- `~/.preferred-shell` is read by `.bashrc` (verified). No `chsh` alias or function exists in `home/dot_zsh/config/` (searched, none found). Nothing in the `machine` CLI writes `~/.preferred-shell` (not verified in detail).
- The handoff-check cache watches `~/.preferred-shell`, so a changed value is picked up (verified).

**Suggestion:** if wanted, add a small `chsh` wrapper in the work-only module (`01_work.zsh`, which is already limited to the work-machine profile) that writes `~/.preferred-shell` and falls back to the real `chsh` for other users. Reason: low risk, contained to work hosts. It would only help from inside zsh or bash after the config is loaded.

# B. add-zsh-startup-check

## B1. Fresh-install test with a temporary zinit home

**Findings**
- The check runs real `zsh -l -i` with `DOTFILES_ZSH_CHECK=1`, a timeout (`DOTFILES_ZSH_CHECK_TIMEOUT`, default 60 s) and reads the real `~/.local/share/zinit` (verified).
- On a host without `zinit.git` the check is skipped on purpose (first start bootstraps zinit and plugins), tested by `test_fresh_machine_without_zinit_hands_off_unchecked` (verified).
- `.zshrc` clones zinit from GitHub when `ZINIT_HOME` is missing; `ZINIT_HOME` is derived from `XDG_DATA_HOME`, so setting `XDG_DATA_HOME` to a temp directory is enough to redirect it (verified from code). Plugins would be cloned via zinit into the same place and need network.
- Existing tests use stub zsh setups; none runs a real fresh install (verified by listing test names).
- `zsh-recheck --fresh` does not exist; `zsh-recheck` takes no arguments (verified).

**Suggestion:** implement as a separate opt-in command or a CI job (for example the existing Docker tests) using a temporary `XDG_DATA_HOME`, not as a default check. Reason: it is the only test proving a fresh host works, while a default run would clone every plugin and fail on network problems. Run it manually first once to measure the time.

# C. baseline-zsh-plugins-prompt

## C1. Plugin manager and lazy loading

**Findings**
- Turbo (`wait`) is used for: sudo, undollar, zsh-z, git-open, fast-syntax-highlighting, autosuggestions, completions (combined call), history-substring-search, z.lua (`wait'!0'`) (verified, `02_plugins.zsh`).
- Not deferred: powerlevel10k, `ls_colors` pack, zsh-syntax-highlighting, fzf-tab, git-recent, eza, git-recall, fd and diff-so-fancy (`as"program"` entries only add to PATH, cheap) (verified). Powerlevel10k is not deferred because of the instant prompt in `.zshrc` (verified there).
- `.zshrc` runs a second `compinit` at its end and zinit also runs `zicompinit` in a hook; potential double compinit is unverified.
- No startup time measurement exists in the repo (searched for none).

**Suggestion:** measure first (`zsh -i -c exit` with `zprof`, or `hyperfine`) and only then look at changing the manager. Reason: nothing documented shows a startup problem; antidote/sheldon comparison is only worth it if a measurement shows plugin loading dominates. Candidates to defer first: fzf-tab and the `ls_colors` pack.

## C2. Overlapping and unneeded plugins

**Findings**
- Present in `02_plugins.zsh`: `agkozak/zsh-z` (loaded for every host with zsh) and `skywind3000/z.lua` (only if lua or luajit exists; `luajit` is in the `zsh-full` apt set). `autojump` is installed by apt in `zsh-full` and mentioned in the `.zshrc` bootstrap hint, but no config in `home/` sources or uses it (verified by search).
- Both `fast-syntax-highlighting` (turbo) and `zsh-syntax-highlighting` (last in `03_theme.zsh`) are loaded (verified). Two syntax highlighters wrap the same ZLE widgets, so one usually wins or they conflict; the net effect here is unverified.
- `home/dot_bashrc` also initialises z.lua for bash, so z.lua has a role in both shells; zsh-z only in zsh.
- Which of them the owner actually uses (`z` command): unknown. The commands `z` from zsh-z and z.lua would collide; the later load (z.lua) probably defines it (unverified).

**Suggestion:** check `type z` in an interactive session and `zinit report`; then keep one jump tool (z.lua keeps bash and zsh consistent, hypothesis) and one syntax highlighter (fast-syntax-highlighting, since the other is loaded last and may not be needed; unverified). Drop `autojump` from the apt set only if no use is confirmed. Reason: fewer plugins, fewer conflicts; the owner must confirm what is used.

## C3. fzf structure

**Findings**
- Zsh: `02_plugins.zsh` sources the first existing key-bindings and completion file from `/usr/share/doc/fzf/examples`, `/usr/share/fzf`, `~/.fzf/shell`. Bash: the same list in `dot_bashrc` (verified). The comment says distro fzf is used "to avoid zinit-pack build issues" (a code comment, not an owner statement).
- `~/.local/share/zinit/plugins` here also has `fzf` and `junegunn---fzf` directories left from an earlier zinit-based setup (verified on this host; not referenced by current code).
- `Aloxaf/fzf-tab` is loaded right after, using `ftb-tmux-popup`; it needs fzf and tmux (tmux is in `zsh-full`) (verified). Without tmux the popup mode falls back or fails (unverified).
- On hosts without `zsh-full` (no fzf) all of this is skipped except `fzf-tab`, which is loaded regardless (verified).

**Suggestion:** guard `fzf-tab` with the same `command -v fzf` check, and optionally remove the stale zinit fzf directories. Reason: fzf-tab without fzf has no function. Leave the path lists as they are; they cover Debian/Ubuntu and Arch layouts.

## C4. Skipped prompt profiles

**Findings**
- `home/.chezmoiignore` excludes `.p10k.zsh` and `.config/starship.toml` for profiles `rpi-zero` and `container` (verified). `03_theme.zsh` still loads powerlevel10k and sources `~/.p10k.zsh` only `[[ ! -f ]] ||`, so on those profiles p10k is cloned but runs with its default wizard/no config (the first run would start `p10k configure`; unverified).
- Starship is installed by Ansible only if the `starship` feature is selected (`ansible/roles/user_tools/tasks/main.yml`); the `rpi-zero` profile does not list `starship` (verified), so Starship is not installed by default there. For other profiles it depends on the answers (confirms "Open question": not default by profile, verified from the feature model, defaults for other profiles not checked).
- Hypotheses for why: container installs repeat per container (the owner's own hypothesis, unconfirmed); `rpi-zero` could be a performance choice (hypothesis only, nothing in git history or the Readme says so).

**Suggestion:** decide per profile. If no prompt is wanted, also skip loading powerlevel10k in `03_theme.zsh` when `~/.p10k.zsh` is missing; otherwise install the files. Reason: today the plugin is downloaded and loaded without its config, which gets neither the cost saving nor the look.

## C5. Syntax highlighting order

**Findings**
- `03_theme.zsh` says "Ensure zsh-syntax-highlighting is loaded last" (code comment, no stated reason). The plugin documentation (general knowledge, not re-fetched here) says it must be sourced after other widget-wrapping plugins; this is unverified in this session.
- `fast-syntax-highlighting` is also loaded, in turbo mode, i.e. after the prompt, so in practice it loads later than "last" (verified from the `wait` ice).

**Suggestion:** resolve together with C2. If only one highlighter remains, the ordering question becomes the plugin's documented rule (use turbo with `wait` after other plugins). Reason: having two highlighters makes any order unreliable.

## C6. Prompt-mark stripping does not work

**Findings**
- `zpm-zsh/undollar` defines `alias $=''` (verified in the installed plugin). The `❯` handling is a function `'❯'() { "$@" }` in `02_plugins.zsh` added by commit `1ad4df8` (a short single-line commit message without owner motivation).
- Verified here: in `zsh -ic` the function exists (`whence -w ❯` → function) and `❯ echo hi` prints `hi`. The `$` alias is not yet defined in that test because the plugin is turbo-loaded after the first prompt (`$ echo hi2` → command not found); this is expected for `-c` and is not a proof of failure in a real session.
- So the function works in isolation. Why it fails when pasting is not verified. Hypotheses (unconfirmed): the pasted text carries a trailing space or a non-breaking space after `❯`; the p10k prompt char differs (`❯` is the OK/INS char in `.p10k.zsh`, but the vi-command char is `❮` and `▶`/`V` for others); bracketed paste inserts text the line editor treats as quoted so alias/function lookups still apply, but autosuggest or correction (`ENABLE_CORRECTION=true`) could intervene; two-line prompts copied with the path line are not covered.

**Suggestion:** reproduce in a real terminal: paste `❯ echo hi`, then run `type ❯` and `alias $`; compare with a non-breaking space variant. Fix as its own change once the cause is known. Reason: the function itself is correct, so the failure is in the input, not the definition. Consider also covering `$` before the plugin loads, by defining the alias directly.

## C7. One prompt look

**Findings**
- Zsh uses powerlevel10k with `~/.p10k.zsh` and a `prompt_dockerenv` segment (🐳) in `03_theme.zsh` (verified); bash uses Starship (`eval "$(starship init bash)"` in `dot_bashrc`) when installed. `home/dot_config/starship.toml` uses the same `❯` char with different colours (blue success, orange error) (verified).
- Starship supports zsh too, so one tool could serve both shells; whether it keeps the instant-prompt speed of p10k is unmeasured. p10k does not support bash.
- The Docker marker would need Starship's `container` module or a custom module (Starship has a built-in `container` module; general knowledge, not tested here).

**Suggestion:** leave as is until C1 measurements exist. If a single prompt is wanted, try Starship in zsh on one host and compare startup and look. Reason: p10k's instant prompt is the main reason to keep it; replacing it is a trade-off the owner should judge by feel and timing.
