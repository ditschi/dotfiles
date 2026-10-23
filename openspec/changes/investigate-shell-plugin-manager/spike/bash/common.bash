# Shared by both bash variants (spike): options, history, keys, tools, prompt.
HISTFILE=~/.bash_history HISTSIZE=50000 HISTFILESIZE=50000 HISTCONTROL=ignorespace:erasedups
shopt -s histappend autocd cdspell dirspell checkwinsize globstar

SPIKE_CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/spike-bash
# Source the output of `cmd...`, regenerated when the binary is newer than the cache.
spike_cache_eval() {
  local name=$1; shift
  local bin f=$SPIKE_CACHE/$name.bash
  bin=$(type -P "$1") || return 0
  if [[ ! -s $f || $bin -nt $f ]]; then
    mkdir -p "$SPIKE_CACHE" && "$@" >"$f"
  fi
  source "$f"
}

# undollar: `$` cannot be a bash function or alias; the not-found handler runs in a subshell,
# so `$ cd dir` does not change the directory. `❯` works as a function.
command_not_found_handle() {
  if [[ $1 == '$' ]]; then shift; "$@"; return; fi
  printf 'bash: %s: command not found\n' "$1" >&2
  return 127
}
'❯'() { "$@"; }

# LS_COLORS: bash needs no plugin manager; reuse the checkout of the zsh plugin manager.
spike_lscolors() {
  local src=$1 f=$SPIKE_CACHE/lscolors.bash
  [[ -r $src ]] || return 0
  [[ -s $f && ! $src -nt $f ]] || dircolors -b "$src" >"$f"
  source "$f"
}

spike_lscolors "${XDG_DATA_HOME:-$HOME/.local/share}/sheldon/repos/github.com/trapd00r/LS_COLORS/LS_COLORS"
spike_cache_eval starship starship init bash --print-full-init
spike_cache_eval fzf fzf --bash
spike_cache_eval zoxide zoxide init bash
# atuin (alternative to fzf Ctrl+R; needs no bash-preexec since 18.x)
[[ -n ${SPIKE_ATUIN-} ]] && spike_cache_eval atuin atuin init bash

# Measurement only: SPIKE_T0/SPIKE_REPORT, exit at the first prompt with SPIKE_EXIT_AT_PROMPT.
spike_bash_prompt() {
  if [[ -n ${SPIKE_T0-} && -n ${SPIKE_REPORT-} ]]; then
    local now=${EPOCHREALTIME/,/.}
    echo "prompt_ms=$(awk "BEGIN{print ($now - ${SPIKE_T0/,/.}) * 1000}") $(spike_bash_features)" >>"$SPIKE_REPORT"
  fi
  [[ -n ${SPIKE_EXIT_AT_PROMPT-} ]] && kill -HUP $$
  PROMPT_COMMAND=("${PROMPT_COMMAND[@]/spike_bash_prompt}")
}
spike_bash_features() {
  local out=() k
  out+=("blesh=$([[ ${BLE_VERSION-} ]] && echo 1 || echo 0)")
  out+=("ls_colors=$(( ${#LS_COLORS} > 1000 ))")
  out+=("fzf_history=$(bind -X 2>/dev/null | grep -q fzf || [[ ${BLE_VERSION-} ]] && echo 1 || echo 0)")
  out+=("zoxide=$(declare -F __zoxide_z >/dev/null && echo 1 || echo 0)")
  out+=("atuin=$(declare -F __atuin_history >/dev/null && echo 1 || echo 0)")
  out+=("starship=$([[ ${STARSHIP_SHELL-} == bash ]] && echo 1 || echo 0)")
  echo "${out[*]}"
}
