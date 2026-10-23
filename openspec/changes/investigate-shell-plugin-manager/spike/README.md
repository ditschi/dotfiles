# Shell plugin-manager spike

Harness for the investigation `investigate-shell-plugin-manager`. Nothing here touches `home/`.

## Layout

| Path | Purpose |
|------|---------|
| `Dockerfile` | Benchmark image `shell-spike:local` (Ubuntu 24.04, zsh-bench, tools from mise, ble.sh) |
| `bench.sh` | `bench.sh container|host <config>...`: runs a config through zsh-bench and the warm/cold runs, writes `results/<config>.<mode>.{raw,json}` |
| `summarize.py` | Raw output to JSON (median/p90 after 3 warm-ups) or a table line (`--line`) |
| `gen-variants.py` | Generates the per-plugin ladder (`configs/ladder-*`) and the alternatives (`configs/alt-*`), both git-ignored |
| `configs/_common/` | Shared: `setup.zsh` (install + warm runs), `.zshenv`, `.zsh/common.zsh` (options, keys, zstyles, helpers), `.zsh/spike-marker.zsh` (measurement only), `starship.toml` |
| `configs/{base-prompt,zinit,antidote,sheldon}/` | The candidates (`setup` + `skel/` copied into `$HOME`) |
| `configs/baseline-current/` | The current dotfiles setup, staged from `home/` by `bench.sh` |
| `check-interactive.sh` | Key-driven feature checks in tmux, writes `results/<config>.interactive.txt` |
| `bash/` | Bash variants (`fallback.bashrc`, `full.bashrc` with ble.sh, shared `common.bash`) and `bench-bash.sh` (task 5) |
| `prompt-capture.sh` | Renders the shared Starship prompt for zsh and bash, host and container (task 5.3) |
| `diff-compare.sh` | diff-so-fancy vs delta (task 3.3) |
| `tools-install.sh` | Tool installation via mise / zinit gh-r / mix, offline and missing-tool checks (task 4.1) |
| `results/` | Raw and summarised results |

Task 2.x mentions `spike/<candidate>/`; the candidates live in `spike/configs/<candidate>/` because zsh-bench expects one config directory.

## Run

```sh
docker build -t shell-spike:local .
ITERS=13 ./bench.sh container base-prompt zinit antidote sheldon
ITERS=13 ./bench.sh host baseline-current zinit antidote sheldon   # temporary HOME, ~/.zshrc untouched
python3 gen-variants.py && ./bench.sh container $(cd configs && ls -d ladder-* alt-*)
python3 summarize.py --line results/*.raw
./check-interactive.sh zinit antidote sheldon
./bash/bench-bash.sh && ./prompt-capture.sh && ./diff-compare.sh && ./tools-install.sh
```

## What is measured

Per config, `setup` (run by zsh-bench as a fresh user) does:

1. **Cold install**: first `zsh -li` with empty plugin directories, until every deferred plugin is loaded
   (`install_ms`; `install_rc=124` means it never finished within 300 s).
2. **Warm runs**: 13 more starts; the first 3 are dropped. Reported per run:
   - `prompt_ms`: start until ZLE accepts input (`line-init`), i.e. "I can type and the keys are handled".
   - `loaded_ms`: start until the last deferred step ran (`spike_loaded`), i.e. "everything works".
   - a feature self-check at that point (see checklist).
3. zsh-bench (`--iters`, first 3 dropped): `first_prompt_lag_ms` (first prompt drawn; counts a
   Powerlevel10k instant prompt), `command_lag_ms`, `input_lag_ms`, `exit_time_ms`.
   zsh-bench runs in a generated git repository, so its prompt numbers include the git segment.

zsh-bench's `has_*` flags and `first_command_lag_ms` do not reflect deferred plugins: its own `zinit-turbo`
and `zsh-defer` reference configs report `has_syntax_highlighting=0`. The spike uses its own `loaded_ms`
and feature check instead.

## Feature checklist (task 2.x)

Automated in `spike_features` (`results/*.json` → `features`, `summarize.py --line` prints `ok` or the missing items):

| Feature (proposal.md) | Check |
|-----------------------|-------|
| Completion system | `compdef` defined (`compsys`) |
| fzf-tab, cd preview with eza | `fzf-tab-complete` defined, Tab bound to it (`fzf_tab`, `key_tab`); zstyle in `common.zsh` |
| Autosuggestions, Ctrl+Space accept, Ctrl+_ execute | `_zsh_autosuggest_start`, bindings (`autosuggest`, `key_accept`, `key_execute`) |
| Syntax highlighting (one highlighter) | fast-syntax-highlighting or zsh-syntax-highlighting functions (`highlight`) |
| History substring search on Up/Down | widget and `^[[A` binding (`hss`, `key_up_hss`) |
| Directory jumping | `__zoxide_z` (`zoxide`); alternatives checked by hand |
| Ctrl+R fzf history | `fzf-history-widget` on `^R` (`fzf_history`, `key_ctrl_r`) |
| sudo on Esc Esc | `sudo-command-line` on `\e\e` (`sudo`, `key_sudo`) |
| undollar (`$ ` and `❯ `) | alias `$` (`undollar`); `❯` function in `common.zsh` |
| LS_COLORS | `${#LS_COLORS} > 1000` (`ls_colors`) |
| Correction | `setopt correct` (`correct`) |
| diff-so-fancy / delta | git pager, not a shell plugin (task 3.3) |

Checked by hand in the container (`docker run --rm -it shell-spike:local`, copy a config's `skel/` and `_common/skel/` into `~`):
fzf-tab popup and eza preview on `cd <Tab>`, grey suggestion accepted with Ctrl+Space, highlighting colours,
Esc Esc prepends `sudo`, pasting `$ ls` and `❯ ls` runs `ls`, `z <dir>` jumps.
