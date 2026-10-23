# Tasks

## 1. Harness

- [ ] 1.1 Create `spike/Dockerfile` extending `tests/docker/Dockerfile` with zsh-bench, hyperfine, mise, fzf and eza. Verify `docker build` succeeds and `zsh-bench` runs inside the container against a minimal zshrc.
- [ ] 1.2 Write `spike/bench.sh`. It runs one config (path to a `ZDOTDIR`) in the container or on the host with a temporary `ZDOTDIR`/`XDG_DATA_HOME`/`XDG_CACHE_HOME`, runs zsh-bench (3 warm-ups, at least 10 runs) and writes median and p90 to `spike/results/<name>.json`. Verify a run on the host leaves `~/.zshrc` and `~/.local/share/zinit` unchanged (compare mtime or hash before and after).
- [ ] 1.3 Add a cold-install mode to `bench.sh` (empty data dirs, hyperfine for the first start). Verify it reports an install time for the minimal config.
- [ ] 1.4 Record the baseline: the current real setup (`home/dot_zshrc` and modules) through `bench.sh` on the host. Verify the numbers are in `spike/results/baseline-current.json`.

## 2. Candidates with the same feature list

- [ ] 2.1 Write `spike/zinit/` from scratch (turbo, one highlighter last, one cached compinit, fzf-tab after compinit). Verify every item of the feature list in proposal.md works by hand in the container (checklist in `spike/README.md`).
- [ ] 2.2 Write `spike/antidote/` (plugins file and zsh-defer) with the same feature list. Verify with the same checklist.
- [ ] 2.3 Write `spike/sheldon/` (`plugins.toml` and zsh-defer) with the same feature list. Verify with the same checklist.
- [ ] 2.4 Run `bench.sh` warm and cold for the three candidates in the container and on the host. Verify the results files exist, and add a comparison table to design.md (Findings) with lines of config per candidate.

## 3. Cost per plugin and head-to-head alternatives

- [ ] 3.1 Build the per-plugin ladder (minimal zshrc, then one plugin added per step in final order, each loaded directly and deferred) on the fastest candidate from 2.4. Verify the per-plugin cost table in design.md lists every plugin with its added `first_prompt_lag` and `first_command_lag`.
- [ ] 3.2 Measure the alternatives on the same base:
  - zsh-z / z.lua / zoxide
  - fast-syntax-highlighting / zsh-syntax-highlighting
  - Powerlevel10k (instant prompt) / Starship
  - fzf Ctrl+R / atuin
  - cached / uncached compinit
  - `mise activate` / mise shims

  Verify each group has a row in the design.md table.
- [ ] 3.3 Compare diff-so-fancy and delta on a sample repository diff (runtime with hyperfine, readability by eye). Verify the result is recorded.
- [ ] 3.4 Check the Powerlevel10k maintenance status upstream and record it with its date in design.md.

## 4. Tool installation

- [ ] 4.1 Install the shell tools (fzf, eza, fd, zoxide, starship, atuin, delta) three ways in the container (mise; the plugin manager; a mix) as a non-root user. Verify for each variant: install time, works without root, arm64 assets exist, the shell starts offline after install, and with one tool removed the shell starts without errors. Record a table in design.md.

## 5. Bash parity and shared prompt

- [ ] 5.1 Build the near-equal bash: sheldon (bash), ble.sh, the same Starship config, `fzf --bash`, zoxide, atuin. Measure `bash -i` first-prompt time with hyperfine and check the feature list by hand. Record the results and gaps in design.md.
- [ ] 5.2 Build the fallback bash (Starship, `fzf --bash`, zoxide, atuin, no ble.sh) and measure it the same way. Verify the result is recorded next to 5.1.
- [ ] 5.3 Write one `spike/starship.toml` used by both shells, with the Docker marker (`container` or a custom `/.dockerenv` module), `env_var.DOTFILES_UPDATE_SEGMENT`, and a prompt character coloured per shell. Verify by screenshot or text capture in both shells inside and outside a container.

## 6. Rust tool survey

- [ ] 6.1 Survey current command-line tools against the criteria in design.md (release in the last 12 months, stable versions, x86_64 and arm64 binaries, in mise/aqua, a daily benefit). Verify the table in design.md lists each tool with a keep or skip recommendation and its source link.

## 7. Recommendation and decision

- [ ] 7.1 Write the recommendation in design.md (Findings): plugin manager, plugin set, prompt, tool installation, bash level, and suggested Rust tools, each backed by the measured numbers and the 50 ms / 300 ms targets. Verify every recommendation cites a results file or table.
- [ ] 7.2 Ask the owner to decide each point (ask_user form) and write the decisions under **Decision** in design.md. Note any impact on `adopt-mise` and `investigate-shell-layout`. Verify every open question in proposal.md and design.md is answered or explicitly deferred.
- [ ] 7.3 Run `pre-commit run --all-files` and `pytest tests/unit -q`, and verify both pass (the spike must not touch `home/` or break the repository checks).

## Workflow follow-up

- Propose the implementation change (spec deltas for `zsh-plugins`, `shell-prompt`, `bash-shared-config`, `zsh-config-loading`, `shell-handoff` as decided), and update `adopt-mise` if tool installation changes.
- Archive this investigation after the decision is recorded.
