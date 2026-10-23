# Design

## Context

See proposal.md (Why, What Changes) for motivation and scope.

Current state relevant to the method:

- zsh loads zinit from `home/dot_zshrc`, then every module in `home/dot_zsh/config/` by glob (`00_LOADER.zsh`). Plugins live in `02_plugins.zsh` and `03_theme.zsh`. The Powerlevel10k instant prompt is sourced at the top of `.zshrc`, and a second `compinit` runs at its end.
- bash (`home/dot_bashrc`) loads a hard-coded subset of the modules, fzf from distribution paths, z.lua when lua exists, and Starship when installed.
- The bash-to-zsh handoff (`zsh-handoff-check.sh`, spec `shell-handoff`) checks zinit and sets `DOTFILES_ZSH_LOADED`. Any replacement must keep an equivalent "config loaded" signal.
- The Docker image `tests/docker/Dockerfile` (Ubuntu 26.04, zsh, git, curl) is the existing container base.
- The host has `docker`, `starship` and `zoxide`. `hyperfine`, `mise`, `sheldon` and `atuin` are not installed.
- Measured once during exploration on the owner's host: `zsh -i -c exit` takes about 0.5 s warm and 2.4 s cold. This excludes everything zinit loads in turbo mode.

## Goals / Non-Goals

**Goals:**
- Comparable numbers for each candidate and each plugin, produced by a script that can be re-run.
- Configurations short enough that "ease of maintenance" can be judged by reading them.
- A recommendation the owner can decide on, with the data behind it.

**Non-Goals:**
- Changing `home/`, the specs or `adopt-mise` in this change.
- Benchmarking on rpi or rpi-zero hardware. Relative results from the container are used, and a check on slow hardware becomes a task of the implementation change if needed.
- Tuning Powerlevel10k or Starship themes beyond the agreed prompt elements.

## Decisions

### Build every candidate from one feature list, from scratch

The candidates are zinit with turbo, antidote with zsh-defer, and sheldon with zsh-defer. Each is written new against the feature list in proposal.md, not ported from `02_plugins.zsh`, because the current file may load plugins in the wrong order or with wrong ices. The rules that every candidate follows:

- Exactly one syntax highlighter, loaded last.
- `compinit` once, with a cached dump.
- Autosuggestions bound after loading.
- fzf-tab loaded after `compinit` and before the plugins that wrap widgets.

The zinit build doubles as a cleaned-up reference, so "keep zinit, fix the configuration" is also measured.

### Measure with zsh-bench, hyperfine and a per-plugin ladder

- **zsh-bench (romkatv)** measures what a user notices: `first_prompt_lag`, `first_command_lag`, `command_lag` and `input_lag`. `first_prompt_lag` answers "when can I type", and `first_command_lag` with deferred loading answers "when is everything loaded". `zsh -i -c exit` alone is rejected because it skips deferred plugins and the prompt.
- **hyperfine** measures the first start on an empty home (install time) and the plain `bash -i -c exit` / `zsh -i -c exit` times as secondary numbers.
- **Per-plugin ladder:** start from a minimal zshrc (`compinit` and the prompt), add one plugin at a time in the final order, and record the change in each zsh-bench metric. A plugin is measured both loaded directly and deferred, so the price list shows what deferral saves.
- **Head-to-head pairs:** each pair or group from proposal.md is measured on the same base. The base is the "price list" config, with only the compared item swapped.
- **Runs:** 3 warm-ups and at least 10 measured runs per data point. Report median and p90.

Targets for pass or fail: `first_prompt_lag` under 50 ms, and fully loaded (`first_command_lag`) under 300 ms.

### Two environments: container for comparison, host for reality

- The container gives reproducible cold installs and a clean home per run. It extends `tests/docker/Dockerfile` with the benchmark tools, and the network is allowed only during install runs.
- The owner's host gives the real daily numbers. It uses a temporary `ZDOTDIR` and `XDG_DATA_HOME`/`XDG_CACHE_HOME`, so the live zinit installation and `~/.zshrc` stay untouched.

### Tool installation compared as three variants

For the tools the shell needs (fzf, eza, fd, zoxide, starship, atuin, delta), three variants are compared:

- **mise:** a `mise.toml` in the harness, either `mise activate` or shims.
- **Plugin manager:** zinit `gh-r`, sheldon `remote`/`github` release downloads where possible, and antidote with its fallback.
- **Mix:** the plugin manager installs plugin-coupled tools such as fzf for fzf-tab, and mise installs the rest.

Each variant is judged on:
- first-install time
- whether it works without root
- arm64 availability (from release assets)
- the shell starting offline after install
- the behaviour when one tool is missing (the shell must start and the feature degrades without errors)

### Bash parity evaluated at two levels

- **Near-equal:** sheldon with a bash profile plus ble.sh (autosuggestions, highlighting, fzf completion), with the same Starship configuration. This is measured with the same metrics, using `bash -i` and hyperfine for time to the first prompt.
- **Fallback:** Starship, `fzf --bash`, zoxide, atuin and the shared modules. This is also measured.

The prompt differences between the shells are limited to the prompt character colour, set by a Starship variable per shell. The Docker marker uses Starship's `container` module or a custom module that checks `/.dockerenv`. The update segment uses the existing `env_var.DOTFILES_UPDATE_SEGMENT`.

### Rust tool survey with fixed criteria

Candidates come from current lists (for example the "modern unix" collections) and from the tools already in use. Each candidate is kept if:

- it had a release in the last 12 months
- it publishes stable versions
- it has prebuilt binaries for x86_64 and arm64
- it is available in mise or aqua
- it clearly improves something done daily

The result is a table with a recommendation per tool; nothing is installed into `home/`.

### Where the spike lives and where results go

- The harness lives in this change under `spike/`: the Dockerfile, one directory per candidate, the ladder configs and `bench.sh`. It is archived with the change, so the numbers stay reproducible. The session workspace was rejected because it is not archived.
- The benchmarks may download from public GitHub and the mise/aqua registries, both on the host and in containers.
- Raw results go to `spike/results/` as JSON or CSV.
- The summary tables, the recommendation and the owner's decision are added to this design.md under **Findings** and **Decision**.
- The implementation becomes a separate change with spec deltas (see proposal.md, Capabilities). If the decision affects tool installation, it also updates `adopt-mise`.

## Risks / Trade-offs

- [Container numbers differ from host numbers (filesystem, CPU)] → Use the container only for relative comparisons; take the absolute targets from the host runs.
- [zsh-bench needs a real TTY and may not run in plain `docker run`] → zsh-bench runs zsh in its own pseudo-terminal; if that fails, run it inside the host with a temporary `ZDOTDIR` only.
- [Deferred loading hides cost instead of removing it; `input_lag` can suffer while plugins load] → Report `input_lag` and `command_lag`, not only the first-prompt numbers.
- [Network variance distorts cold-install numbers] → Repeat install runs, report the median, and note that install time is a secondary criterion.
- [ble.sh is large and can slow bash noticeably] → Measured explicitly; the fallback level remains acceptable.
- [The recommendation contradicts `adopt-mise` (tools from mise)] → Record it as an open point for the owner; `adopt-mise` is not changed in this spike.
- [Powerlevel10k maintenance status] → Check upstream status (README, recent commits) and record it as a fact with its date.

## Open Questions

- Should the Rust tools suggested by the survey go into the implementation change, or into a separate small change per tool?

## Findings

Measured 2026-10-23. Raw data in `spike/results/` (`<config>.<container|host>.raw/.json`, `run-all.log`, `rerun-candidates.log`); how to re-run is in `spike/README.md`. Times are median/p90 in ms over 10 measured runs after 3 warm-ups.

### Deviations from the method

- The spike image (`spike/Dockerfile`) is based on `ubuntu:24.04` with the tools from `mise`, not on `tests/docker/Dockerfile`; it only needs zsh, the tools and zsh-bench.
- Config directories are `spike/configs/<cfg>/`, not `spike/<cfg>/`.
- zsh-bench's `has_*` flags and `first_command_lag` do not see plugins loaded by zsh-defer or turbo (zsh-bench's own `zinit-turbo` and `zsh-defer` reference configs report no highlighting either). The harness therefore adds its own marker (`spike-marker.zsh`): **prompt** = time to the first `zle-line-init` (the user can type), **loaded** = time until the last deferred step ran, plus a self-check of every feature and key binding. zsh-bench's `first_prompt_lag` (**zb-prompt**), `command_lag` and `input_lag` are still reported.
- The install time is measured by each config's `setup` (first start on an empty home until fully loaded, including downloads), not with hyperfine.
- zsh-bench runs inside a generated Git repository, so `command_lag` and zb-prompt include Starship's `git_status` (about 25 ms per prompt).
- zsh-bench hung once in one of its own iterations (sheldon, container); `bench.sh` now retries once after a 600 s timeout.

### Candidates (task 2.4)

All three candidates provide the full feature list; the automated check (`features ok`) and the interactive tmux checks (`spike/results/<cfg>.interactive.txt`: LS_COLORS, paste of `$ `/`❯ ` lines, Esc Esc sudo, Ctrl+Space accept, Up substring search, `z`, fzf-tab list and preview, Ctrl+R, correction) pass for each.

| Config | Env | prompt | loaded | zb-prompt | command_lag | input_lag | first install | Lines of config¹ |
|---|---|---|---|---|---|---|---|---|
| current setup (`home/`) | host | 507.5/542.4 | 947.3/979.4 | 8.3 (p10k instant prompt) | 19.1 | 6.5 | 56 s | 02_plugins.zsh + 03_theme.zsh + p10k |
| zinit (rebuilt, turbo) | host | 33.5/38.2 | 160.9/171.3 | 53.8 | 25.9 | 4.9 | 15.8 s | 20 |
| antidote + zsh-defer | host | 22.8/24.5 | 99.3/102.2 | 36.4 | 25.1 | 4.5 | 6.0 s | 21 (12 + 9) |
| sheldon + zsh-defer | host | 20.6/21.9 | 93.5/95.9 | 35.1 | 25.5 | 4.3 | 3.2 s | 46 (10 + 36) |
| zinit | container | 38.3/43.6 | 182.2/196.8 | 64.5 | 34.7 | 6.5 | 20.4 s | |
| antidote | container | 22.2/24.8 | 106.7/109.3 | 43.9 | 34.3 | 5.0 | 4.1 s | |
| sheldon | container | 19.8/22.4 | 92.4/99.3 | 42.5 | 33.5 | 4.5 | 3.1 s | |
| prompt only (Starship, no plugins) | container | 34.3/37.1 | – | 62.8 | 36.3 | 0.2 | 0.5 s | |

¹ Non-comment lines of the plugin-manager part; all candidates share `common.zsh` (69 lines: options, history, compinit, tool init, key bindings) and `starship.toml` (33 lines).

- The current setup misses the targets by a factor of 10 (prompt 508 ms, loaded 947 ms). Its p10k instant prompt shows a prompt image after 8 ms, but input is only processed after 508 ms. It also lacks working `correct` (needs oh-my-zsh's `ENABLE_CORRECTION`), the Tab binding check and zoxide.
- All three rebuilt candidates meet both targets (prompt < 50 ms, loaded < 300 ms). antidote and sheldon are equal within noise; zinit costs about +12 ms to the prompt and +65 ms to "loaded", and its first install is 3–5× slower.
- The prompt-only config is slower to the prompt than the candidates because it runs `compinit` before the first prompt; the candidates defer it.

Maintenance (git history, 2026-10-23):

| Project | Commits 2026 | Last commit | Last release |
|---|---|---|---|
| zinit | 143 | 2026-10-15 | v3.17.1, 2026-10-10 |
| antidote | 255 | 2026-09-16 | v2.3.0, 2026-08-07 |
| sheldon | 4 | 2026-07-01 | 0.8.5, 2025-07-22 |
| zsh-defer (used by antidote and sheldon) | 0 | 2024-02-10 | none (small, finished) |

Ease of use: antidote's plugin list is one line per plugin (`repo kind:defer`, hooks `pre:`/`post:`), sheldon needs TOML tables plus Tera templates for anything beyond `source`, zinit needs ices (`atinit`, `atload`, `blockf`, `id-as`, `wait`), and the ID parser treats `sharkdp/fd` as the `sh` ice unless it is written `@sharkdp/fd` (found in task 4.1).

### Cost per plugin (task 3.1)

Ladder on sheldon, adding one plugin per step in the final order (`spike/results/ladder-*.container.*`). Sync = loaded before the prompt (cost shows in **prompt**); defer = loaded by zsh-defer (cost shows in **loaded**, prompt stays 18–20 ms).

| Step | Sync: Δ prompt | Defer: Δ loaded | Note |
|---|---|---|---|
| base (Starship, history, options) | 24.5 | 25.9 | |
| zsh-completions (fpath) | ±0 | ±0 | |
| LS_COLORS (cached `dircolors`) | +0.4 | +0.6 | |
| compinit (cached dump) | +17.8 | +17.3 | single largest item besides autosuggestions |
| fzf (`fzf --zsh`, cached) | +4.3 | +2.8 | |
| zoxide (cached init) | ±0 | ±0 | |
| fzf-tab | +4.1 | +6.8 | |
| zsh-sudo | ±0 | ±0 | 3-line plugin, last push 2022 |
| undollar | +2.5 | +1.0 | it is one alias `$=''`; inline it |
| history-substring-search | ±0 | ±0 | |
| zsh-autosuggestions | +25.6 | +22.1 | input_lag 0.2 → 1.4 |
| fast-syntax-highlighting | +12.8 | +13.4 | input_lag 1.4 → 5.0 |
| **total** | prompt 88.3 | loaded 87.9, prompt 17.7 | |

Loading everything synchronously would already miss the 50 ms prompt target (88 ms); deferral keeps the prompt at the base cost.

### Alternatives (task 3.2)

Each row swaps one item in the sheldon config (container; reference: sheldon prompt 19.8, loaded 92.4, input_lag 4.5).

| Group | Variant | prompt | loaded | input_lag | Note |
|---|---|---|---|---|---|
| directory jump | zoxide (reference) | 19.8 | 92.4 | 4.5 | Rust binary, also for bash, in mise |
| | zsh-z | 17.4 | 93.0 | 5.5 | zsh only |
| | z.lua | 18.6 | 102.6 | 4.6 | needs lua |
| highlighter | fast-syntax-highlighting (reference) | 19.8 | 92.4 | 4.5 | |
| | zsh-syntax-highlighting | 19.5 | 76.3 | 14.7 | loads faster, 3× input lag while typing |
| prompt | Starship (reference) | 19.8 | 92.4 | 4.5 | command_lag 33.5 (includes git_status) |
| | Powerlevel10k, instant prompt | 64.6 (zb-prompt 7.4) | 136.1 | 7.5 | command_lag 9.1 (async gitstatusd); prompt image at 7 ms, typing possible at 65 ms |
| history search | fzf Ctrl+R (reference) | 19.8 | 92.4 | 4.5 | |
| | atuin | 18.4 | 97.7 | 4.4 | replaces Ctrl+R (check `key_ctrl_r` expects fzf); own database, sync optional |
| compinit | cached dump (reference) | 19.8 | 92.4 | 4.5 | |
| | uncached | 18.9 | 95.5 | 4.8 | +3 ms when deferred |
| tool activation | tools on PATH (reference) | 19.8 | 92.4 | 4.5 | |
| | `mise activate zsh` | 36.7 | 109.3 | 4.5 | +17 ms prompt, as in adopt-mise (~20 ms) |
| | mise shims on PATH | 18.8 | 93.7 | 4.3 | no start cost |
| zsh-defer options | `-dmpr` (reference) | 19.8 | 92.4 | 4.5 | |
| | defaults (`12dmszpr`) | 15.8 | 135.1 | 4.3 | precmd hooks and prompt redraw after every step: +43 ms to loaded |

diff pager (task 3.3, `spike/results/diff-compare.txt`): on a 17,098-line diff, diff-so-fancy 1.4.14 takes 379 ± 100 ms and delta 0.20.1 469 ± 72 ms; for a normal commit both are instant. delta adds syntax highlighting, line numbers and side-by-side and is a single binary in mise; diff-so-fancy is a Perl script. Readability needs a look by the owner (`git -c core.pager=delta show`).

Powerlevel10k status (task 3.4, checked 2026-10-23): the README states "THE PROJECT HAS VERY LIMITED SUPPORT", "NO NEW FEATURES ARE IN THE WORKS" and "MOST BUGS WILL GO UNFIXED"; recent commits only sync gitstatus. Starship released v1.27.0 on 2026-10-17.

### Tool installation (task 4.1)

`spike/tools-install.sh`, results in `spike/results/tools-install.txt`. fzf, eza, fd, zoxide, starship, atuin and delta, installed as the non-root user `tester` in the container; then started with `--network none`.

| Variant | Install | Without root | arm64 | Offline start | One tool removed |
|---|---|---|---|---|---|
| mise (`mise use -g`, `mise activate`) | 7–11 s | yes | all 7 have linux arm64 assets (survey) | all tools work | shell starts without errors; on first use mise reinstalls the tool from its download cache, even offline; with the cache gone the tool is just missing |
| zinit `from"gh-r"` | 34–36 s | yes | same assets, but asset choice depends on zinit's matching | works | every start tries to download the tool again and prints errors; atuin was not found with `pick"*/atuin"` and eza needed `bpick`, so each tool needs ice tuning |
| mix (zinit gh-r for fzf, mise for the rest) | 12–18 s | yes | as above | works | as mise for mise tools |

antidote and sheldon cannot install release binaries; with them, tools come from mise anyway.

### Bash (tasks 5.1, 5.2)

`spike/bash/` (`common.bash`, `fallback.bashrc`, `full.bashrc`, `bench-bash.sh`; results in `spike/results/bash.txt`). Time from start to the first prompt, container:

| Level | prompt | Cold (first start) | Features |
|---|---|---|---|
| plain bash | 5.8/7.1 | 7 | – |
| fallback: Starship, `fzf --bash`, zoxide, LS_COLORS, readline bindings | 32.5/33.7 | 44 | prefix (not substring) history search on Up, Esc Esc sudo, Ctrl+R fzf, `z`, same prompt |
| fallback + atuin | 55.6/57.7 | 91 | + atuin history |
| near-equal: fallback + ble.sh (autosuggestions, highlighting, substring search, menu completion) | 302.5/325.9 | 788 | ble.sh alone costs about 250 ms |
| near-equal + atuin | 470.2/504.0 | 1008 | |

- bash needs no plugin manager: the only plugin data is LS_COLORS, which can be read from the zsh plugin manager's checkout. sheldon's bash support adds nothing here.
- Gaps of the fallback: no autosuggestions, no highlighting, no fzf-tab (only `fzf --bash` Ctrl+T/Alt+C and `**<Tab>`), prefix instead of substring search. `$ cmd` paste works only through `command_not_found_handle`, which runs in a subshell (so `$ cd dir` does not change the directory); `❯ cmd` works as a function.
- ble.sh brings bash close to zsh but misses the 50 ms target by 6×; it has no release since `v0.4.0-devel3` (2023), only nightly builds (48 commits in 2026).

### Shared prompt (task 5.3)

One `spike/configs/_common/skel/.config/starship.toml` for both shells (`spike/prompt-capture.sh`, output in `spike/results/prompt-capture.txt`):

- prompt character `❯` drawn by the `shell` module: zsh bold green, bash bold purple; the `character` module is disabled and a failed command shows as `✘ERROR` from the `status` module;
- the `container` module shows `🐳` inside Docker and nothing on the host (checked in both shells);
- `env_var.DOTFILES_UPDATE_SEGMENT` is kept.

### Rust tool survey (task 6.1)

Release data from the GitHub API on 2026-10-23 (`spike/results/rust-survey.tsv`). Criteria: release in the last 12 months, stable versions, linux x86_64 and arm64 assets, in the mise registry, daily benefit. "in use" = already referenced in `home/` or `ansible/`.

| Tool | Latest | arm64 | mise | Recommendation |
|---|---|---|---|---|
| [ripgrep](https://github.com/BurntSushi/ripgrep) | 15.2.0, 2026-07 | yes | yes | keep (in use) |
| [fd](https://github.com/sharkdp/fd) | 10.5.0, 2026-08 | yes | yes | keep (in use, fzf source) |
| [bat](https://github.com/sharkdp/bat) | 0.26.1, 2025-12 | yes | yes | keep (previews) |
| [eza](https://github.com/eza-community/eza) | 0.23.5, 2026-07 | yes | yes | keep (in use, fzf-tab preview) |
| [zoxide](https://github.com/ajeetdsouza/zoxide) | 0.10.0, 2026-07 | yes | yes | keep, replaces z.lua (works in bash and zsh) |
| [starship](https://github.com/starship/starship) | 1.27.0, 2026-10 | yes | yes | keep (in use) |
| [atuin](https://github.com/atuinsh/atuin) | 18.24.2, 2026-10 | yes | yes | optional: owner decision (Ctrl+R replacement, +23 ms in bash) |
| [delta](https://github.com/dandavison/delta) | 0.20.1, 2026-10 | yes | yes | candidate to replace diff-so-fancy (task 3.3) |
| [yazi](https://github.com/sxyazi/yazi) | 26.9.1, 2026-09 | yes | yes | keep (in use) |
| [difftastic](https://github.com/Wilfred/difftastic) | 0.71.0, 2026-09 | yes | yes | skip (occasional `git difftool`, not daily) |
| [dust](https://github.com/bootandy/dust) | 1.2.6, 2026-09 | yes | yes | skip (not daily) |
| [procs](https://github.com/dalance/procs) | 0.14.12, 2026-06 | yes | no | skip (not in mise registry) |
| [bottom](https://github.com/ClementTsang/bottom) | 0.14.9, 2026-08 | yes | yes | skip (not daily) |
| [hyperfine](https://github.com/sharkdp/hyperfine) | 2.0.0, 2026-10 | yes | yes | skip (per project) |
| [tokei](https://github.com/XAMPPRocky/tokei) | 15.0.0, 2026-09 | no linux assets in latest release | yes | skip |
| [sd](https://github.com/chmln/sd) | 1.1.0, 2026-02 | yes | yes | skip (sed is enough) |
| [xh](https://github.com/ducaale/xh) | 0.26.3, 2026-10 | yes | yes | skip (curl is enough) |
| [just](https://github.com/casey/just) | 1.59.0, 2026-10 | yes | yes | skip (per project) |
| [gitui](https://github.com/gitui-org/gitui) | 0.28.1, 2026-03 | yes | yes | skip (not in use) |
| [zellij](https://github.com/zellij-org/zellij) | 0.45.1, 2026-08 | yes | yes | skip (tmux in use) |
| [tealdeer](https://github.com/tealdeer-rs/tealdeer) | 1.9.0, 2026-08 | yes | yes | optional (`tldr` pages) |
| [broot](https://github.com/Canop/broot) | 1.61.0, 2026-10 | no linux assets in latest release | yes | skip (overlaps yazi) |
| [navi](https://github.com/denisidoro/navi) | 2.24.0, 2025-01 | yes | yes | skip (no release in 12 months) |
| [television](https://github.com/alexpasmantier/television) | 0.15.9, 2026-06 | yes | yes | skip (overlaps fzf) |
| [skim](https://github.com/skim-rs/skim) | 5.8.0, 2026-10 | yes | yes | skip (fzf-tab needs fzf) |
| [watchexec](https://github.com/watchexec/watchexec) | 2.8.0, 2026-10 | yes | yes | skip (per project) |
| [ouch](https://github.com/ouch-org/ouch) | 0.8.3, 2026-09 | yes | no | skip (not in mise registry) |
| [jaq](https://github.com/01mf02/jaq) | 3.1.2, 2026-10 | yes | yes | skip (jq in use; not fully compatible) |
| [ast-grep](https://github.com/ast-grep/ast-grep) | 0.51.0, 2026-10 | yes | yes | skip (per project) |
| [typos](https://github.com/crate-ci/typos) | 1.51.1, 2026-10 | yes | yes | skip (runs in pre-commit) |
| [sheldon](https://github.com/rossmacarthur/sheldon) | 0.8.5, 2025-07 | yes | yes | fails the 12-month criterion (see plugin manager) |

### Recommendation (task 7.1)

1. **Plugin manager: antidote with zsh-defer.** It meets both targets on the host (prompt 22.8 ms, loaded 99.3 ms; Candidates table), equal to sheldon within noise, has the shortest config (one line per plugin) and is actively maintained (v2.3.0, 255 commits in 2026). sheldon is as fast but has had no release for 15 months and needs Tera templates. Keeping zinit (rebuilt) also meets the targets but is slower (loaded 160.9 ms, install 15.8 s) and has the most complex syntax. Replacing the current setup in any of the three ways improves the start by about 10× (prompt 508 → 20–34 ms).
2. **Plugin set:** keep fzf-tab, zsh-autosuggestions, fast-syntax-highlighting (lower input lag than zsh-syntax-highlighting; Alternatives table), zsh-history-substring-search, zsh-completions, LS_COLORS. Replace z.lua by zoxide. Inline undollar (one alias) and zsh-sudo (one widget) into the shared config instead of loading two unmaintained plugins. Use zsh-defer with `-dmpr`, not its defaults (+43 ms). Fix `correct` by `setopt correct` (missing today).
3. **Prompt: Starship** for both shells with the per-shell `❯` colour and the container marker (Shared prompt). Powerlevel10k gives a faster-looking prompt (7 ms image, 9 ms command_lag in a Git repo) but is in limited-support mode; Starship's cost is about 25 ms per command in a Git repository (Alternatives table).
4. **Tools: from mise** (Tool installation table), as planned in `adopt-mise`. zinit gh-r is 3–4× slower to install, needs per-tool ice tuning and prints errors on every start when a tool is missing. `mise activate` costs about 17 ms at the prompt; shims cost nothing.
5. **Bash: the fallback level** (Starship, `fzf --bash`, zoxide, shared prompt; 32.5 ms). ble.sh (302.5 ms) misses the 50 ms target 6× and has no stable release; it could be an opt-in.
6. **Rust tools:** zoxide replaces z.lua; delta is a candidate to replace diff-so-fancy; atuin and tealdeer are optional; the rest are skipped (Rust tool survey).

## Decision

Decided by the owner on 2026-10-23 (all recommendations of the Findings accepted):

1. **Plugin manager: antidote with zsh-defer (`-dmpr`).** The owner would prefer sheldon only if one config could install the same plugins for bash and zsh. Checked in the spike image: one `plugins.toml` can serve both shells through `profiles` and `SHELDON_PROFILE`, but the only entry bash would use is LS_COLORS; every other plugin is zsh-only and the chosen bash level loads no plugins. So bash and zsh need separate setups either way, and antidote is chosen.
2. **Plugin set:** fzf-tab, zsh-autosuggestions, fast-syntax-highlighting, zsh-history-substring-search, zsh-completions, LS_COLORS; zoxide replaces z.lua; undollar and zsh-sudo are inlined into the shared config; `correct` is set directly.
3. **Prompt:** Starship for zsh and bash with the shared `starship.toml` (per-shell `❯` colour, container marker, update segment); Powerlevel10k is removed.
4. **Tools:** from mise for all tools (no plugin-manager downloads).
5. **Bash:** fallback level (Starship, `fzf --bash`, zoxide, shared prompt); no ble.sh.
6. **Rust tools:** no atuin (fzf Ctrl+R stays); delta replaces diff-so-fancy; optional tools go into the implementation change.

Impact on other changes (not edited here):

- `adopt-mise`: task 1.7 plans ble.sh for bash; by decision 5 it is dropped. `delta` joins the mise tool fragments and diff-so-fancy goes; zoxide already replaces autojump there.
- `investigate-shell-layout`: the zinit `atinit` hook in `02_plugins.zsh` (possible double sourcing of `07_machine.zsh`) disappears with zinit; the new loader order (sync part, then deferred part) should be part of the layout options.
- `shell-handoff`: `zsh-handoff-check.sh` checks zinit; the implementation change needs an equivalent "config loaded" signal for antidote.

Open questions:

- proposal.md, "Is Powerlevel10k still maintained enough to keep?": answered (limited support; replaced by Starship).
- proposal.md, "Does sheldon's bash support together with ble.sh give an experience close enough?": answered (ble.sh costs about 300 ms; fallback chosen; sheldon not needed for bash).
- design.md, "Should the Rust tools go into the implementation change or separate changes?": answered (implementation change).
