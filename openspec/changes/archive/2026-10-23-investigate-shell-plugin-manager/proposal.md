## Why

zinit is hard to configure. It was chosen years ago because it was described as the fastest plugin manager, mainly because of turbo mode: the shell is usable while plugins load in the background. The plugin set is a collection gathered over time and not maintained since; some plugins add commands that are rarely used, and better or faster alternatives may exist now. Bash and zsh also differ widely today (bash has a plain fallback, a different prompt setup and fewer helpers), and one setup that gives both shells almost the same experience is wanted.

This change is a spike: it measures and compares options and records the owner's decision. It does not change the configuration or the specs.

## What Changes

- Define one feature set, derived from the current zinit setup, that every candidate must provide:
  - fzf-tab fuzzy completion with `cd` preview through eza
  - autosuggestions with Ctrl+Space (accept) and Ctrl+_ (execute)
  - one syntax highlighter
  - history substring search on Up/Down
  - directory jumping
  - Ctrl+R fuzzy history
  - sudo on Esc Esc
  - undollar, including pasted `$ ` and `❯ `
  - LS_COLORS
  - `ENABLE_CORRECTION`
  - a side-by-side diff (diff-so-fancy, compared with delta)
- Not in the feature set: git-open, git-recent, git-recall.
- Build each candidate from scratch, not by porting the current files, because the current setup may load plugins in the wrong order or with wrong ices:
  - zinit with turbo
  - antidote with zsh-defer
  - sheldon with zsh-defer
- Measure on a Docker container and on the owner's host with zsh-bench and hyperfine:
  - time to the first prompt
  - time to the first command
  - time until every plugin is loaded
  - first install on an empty host
  - lines and readability of the configuration
- Measure the cost of each plugin separately: start with an empty shell, add one plugin at a time and list the time each one adds.
- Compare plugins and tools that give similar features:
  - zsh-z, z.lua and zoxide
  - fast-syntax-highlighting and zsh-syntax-highlighting
  - Powerlevel10k and Starship
  - fzf Ctrl+R and atuin
  - diff-so-fancy and delta
  - cached and uncached compinit
  - `mise activate` and mise shims
- Compare who installs the tools the shell needs:
  - mise (as planned in `adopt-mise`)
  - the plugin manager (zinit `gh-r`, sheldon or antidote)
  - a mix of both
  - Criteria: hosts without root, arm64, starting offline, and what happens when a tool is missing.
- Evaluate bash parity:
  - Preferred: one tool and one configuration for zsh and bash (for example sheldon with ble.sh).
  - Fallback: tools that support both shells (Starship, fzf, zoxide, atuin).
- Evaluate one Starship prompt for both shells with:
  - the Docker marker
  - the dotfiles update segment
  - a prompt character coloured differently per shell
- Survey current, well-maintained and stable Rust command-line tools and suggest those that improve daily use.
- Record a recommended strategy and the owner's decision. Implementation becomes a separate change.

Targets for daily use: first prompt under 50 ms, all plugins loaded under 300 ms.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. If the decision changes behaviour, the implementation change carries the spec deltas, likely for `zsh-plugins`, `shell-prompt`, `bash-shared-config`, `zsh-config-loading` and `shell-handoff`.

## Impact

- **Code:** none until a decision is made. The spike works in containers and in temporary directories (`XDG_DATA_HOME`, `ZDOTDIR`), not in `home/`.
- **Profiles:** all. Hosts without root (work-machine) and slow hosts (rpi, rpi-zero) matter most for tool installation and startup time.
- **Related changes:**
  - `adopt-mise` (design: tools come from mise, the choice of plugin manager is deferred). The tool-installation comparison may revisit that decision.
  - `investigate-shell-layout` (classification of modules into zsh-only, shared and work). A shared bash/zsh setup depends on that classification.
- **Known problems in the current setup:** `openspec/investigations/shell-and-prompt.md`, sections C1 to C6:
  - two syntax highlighters
  - three directory jumpers (zsh-z, z.lua, autojump)
  - compinit runs twice
  - `07_machine.zsh` may be sourced twice
  - p10k loads on profiles that have no `~/.p10k.zsh`

## Assumptions

- "Turbo where reasonable" means deferred loading for every plugin that is not needed for the first prompt. For antidote and sheldon this is done with zsh-defer.
- The current `zsh -i -c exit` time on the owner's host (about 0.5 s warm, 2.4 s cold, measured once during exploration) is the baseline. It does not include the turbo-loaded plugins.

## Open Questions

- Is Powerlevel10k still maintained enough to keep? Its instant prompt is the main argument for it.
- Does sheldon's bash support together with ble.sh give an experience close enough to zsh, at an acceptable bash startup time?
- Should tools the shell needs be installed by the plugin manager, so the shell installs what it needs, or by mise, so there is one lockfile and no root is needed?
- Which further Rust tools from the survey should become part of the default setup?
