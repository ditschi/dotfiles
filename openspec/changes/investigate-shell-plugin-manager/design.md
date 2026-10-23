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
