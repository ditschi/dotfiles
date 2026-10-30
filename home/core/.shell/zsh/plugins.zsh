alias zshplugins="nano $HOME/.shell/zsh/plugins.txt"

# Plugins are managed by antidote (https://antidote.sh) from ~/.shell/zsh/plugins.txt.
# Everything up to the first prompt is synchronous; fzf-tab, history-substring-search,
# autosuggestions and fast-syntax-highlighting load afterwards through zsh-defer.
# Tools (fzf, zoxide, eza, fd, starship, delta) come from mise and are optional.

ANTIDOTE_HOME=${XDG_DATA_HOME:-$HOME/.local/share}/antidote
_dotfiles_plugins_src=$ZSH/plugins.txt
_dotfiles_plugins_zsh=${XDG_CACHE_HOME:-$HOME/.cache}/zsh/plugins.zsh

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=8,bg=0,bold,underline'
ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_MANUAL_REBIND=1

# Completion (ez-compinit runs compinit from a cached dump; its own styles are off).
zstyle ':plugin:ez-compinit' 'use-cache' 'yes'
zstyle ':plugin:ez-compinit' 'compstyle' 'off'
zstyle ':completion:*' menu no
zstyle ':completion:*:git-checkout:*' sort false
zstyle ':completion:*:descriptions' format '[%d]'
# fzf-tab: preview directories when completing cd (eza when installed), switch groups with , and .
if (( $+commands[eza] )); then
  zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
else
  zstyle ':fzf-tab:complete:cd:*' fzf-preview 'ls -1 --color=always $realpath'
fi
zstyle ':fzf-tab:*' switch-group ',' '.'
zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup

zstyle ':antidote:bundle' use-friendly-names on
# -dmpr: no precmd hooks and no prompt redraw after every deferred step (+43 ms otherwise).
zstyle ':antidote:bundle:*' defer-options '-dmpr'

# --- Hooks named in plugins.txt ---

# Health check (zsh-health.bash, DOTFILES_ZSH_CHECK=1): a `zsh -i -c` never reaches the
# line editor, so queue the deferred steps and run them, in order, at the end of init.zsh.
dotfiles_check_mode_defer() {
  [[ -n ${DOTFILES_ZSH_CHECK-} ]] || return 0
  typeset -ga _dotfiles_deferred=()
  zsh-defer() {
    local opt OPTIND=1 cmd=
    while getopts ':12dmszprat:c:' opt; do
      [[ $opt == c ]] && cmd=$OPTARG
    done
    shift $(( OPTIND - 1 ))
    [[ -n $cmd ]] || cmd=${(j: :)${(q)@}}
    _dotfiles_deferred+=( $cmd )
  }
  dotfiles_run_deferred() {
    local cmd
    for cmd in $_dotfiles_deferred; do eval $cmd; done
    unset _dotfiles_deferred
  }
}

# compinit runs in the deferred init step instead of before the first prompt.
dotfiles_after_ez_compinit() {
  autoload -Uz add-zsh-hook
  add-zsh-hook -d precmd run-compinit
}

# git-recall is not executable in its repository (zinit used to chmod it). Ignore the mode
# change in git so `antidote update` keeps pulling.
dotfiles_after_git_recall() {
  local f=$ANTIDOTE_HOME/Fakerr/git-recall/git-recall
  [[ ! -f $f || -x $f ]] && return 0
  chmod +x $f && git -C ${f:h} config core.fileMode false
}

# LS_COLORS from the trapd00r/LS_COLORS checkout, converted by dircolors and cached.
dotfiles_lscolors() {
  local src=$ANTIDOTE_HOME/trapd00r/LS_COLORS/LS_COLORS
  local f=${XDG_CACHE_HOME:-$HOME/.cache}/zsh/lscolors.zsh
  [[ -r $src ]] && (( $+commands[dircolors] )) || return 0
  if [[ ! -s $f || $src -nt $f ]]; then
    mkdir -p -- ${f:h}
    dircolors -b $src >| $f
  fi
  source $f
  zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
}

# fzf's zsh integration only adds key bindings and widgets, and it saves and restores all
# options including `zle`. Without a terminal (for example the zsh health check of the
# background update, started by a systemd timer) the restore fails with "can't change
# option: zle", and the check would treat that as a broken shell. So load it only with a
# terminal: zsh sets $TTY only when it has one (`-o zle` is on in both cases).
dotfiles_fzf_init() {
  [[ -n $TTY ]] || return 0
  dotfiles_cache_eval fzf fzf --zsh
}

dotfiles_cli_completions() {
  dotfiles_cache_eval copilot copilot completion zsh
  dotfiles_cache_eval zellij zellij setup --generate-completion zsh
  dotfiles_cache_eval gh gh completion -s zsh
  dotfiles_cache_eval opencode opencode --completions zsh
  dotfiles_cache_eval uv uv generate-shell-completion zsh
  dotfiles_cache_eval mise mise completion zsh
  dotfiles_cache_eval lazygit lazygit completion zsh
  dotfiles_cache_eval openspec openspec completion generate zsh
  dotfiles_cache_eval starship-completion starship completions zsh
  dotfiles_cache_eval git-lfs git-lfs completion zsh
}

dotfiles_deferred_init() {
  dotfiles_lscolors
  run-compinit
  source "$DOTFILES_SHELL/zsh/machine-completion.zsh"
  dotfiles_cli_completions
  dotfiles_fzf_init
  dotfiles_cache_eval zoxide zoxide init zsh
}

# pre: hooks run synchronously; this queues the init step in front of fzf-tab.
dotfiles_defer_init() {
  zsh-defer -dmpr dotfiles_deferred_init
}

dotfiles_after_autosuggest() {
  _zsh_autosuggest_start
  bindkey '^ ' autosuggest-accept
  bindkey '^_' autosuggest-execute
}

# Fully loaded; checked by the handoff health check.
dotfiles_deferred_done() {
  typeset -g DOTFILES_ZSH_DEFERRED_LOADED=1
}

# --- Load ---

if [[ ! -r $ANTIDOTE_HOME/mattmc3/antidote/antidote.zsh ]] && (( $+commands[git] )); then
  print -P "%F{33}Installing antidote and the zsh plugins (first start)...%f"
  git clone -q --depth 1 https://github.com/mattmc3/antidote $ANTIDOTE_HOME/mattmc3/antidote
fi
if [[ -r $ANTIDOTE_HOME/mattmc3/antidote/antidote.zsh ]]; then
  source $ANTIDOTE_HOME/mattmc3/antidote/antidote.zsh
  # Rebuild the static plugin file only when plugins.txt changed (clone progress goes to
  # stdout). A failed build (offline) keeps the previous file and is retried next start.
  if [[ ! -s $_dotfiles_plugins_zsh || $_dotfiles_plugins_src -nt $_dotfiles_plugins_zsh ]]; then
    mkdir -p -- ${_dotfiles_plugins_zsh:h}
    if antidote bundle <$_dotfiles_plugins_src 2>&1 >|$_dotfiles_plugins_zsh.new; then
      mv -f -- $_dotfiles_plugins_zsh.new $_dotfiles_plugins_zsh
    else
      rm -f -- $_dotfiles_plugins_zsh.new
    fi
  fi
fi
if [[ -s $_dotfiles_plugins_zsh ]]; then
  source $_dotfiles_plugins_zsh
  # Test and minimal bundles may initialize compinit directly without ez-compinit.
  (( $+functions[run-compinit] )) || source "$DOTFILES_SHELL/zsh/machine-completion.zsh"
else
  # Offline first start: built-in completion and the tool init, no plugins.
  autoload -Uz compinit && compinit -d ${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompdump
  source "$DOTFILES_SHELL/zsh/machine-completion.zsh"
  dotfiles_cli_completions
  dotfiles_fzf_init
  dotfiles_cache_eval zoxide zoxide init zsh
fi
unset _dotfiles_plugins_src _dotfiles_plugins_zsh
