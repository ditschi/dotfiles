# Shared by every candidate: options, keys, completion styles, hooks.
# Plugin managers only decide how and when plugins are fetched and loaded.

setopt auto_cd interactive_comments correct
setopt hist_ignore_space hist_ignore_all_dups share_history extended_history
HISTFILE=~/.zsh_history HISTSIZE=50000 SAVEHIST=50000
bindkey -e

bindkey '^[[3~' delete-char
bindkey '^[[H' beginning-of-line
bindkey '^[[F' end-of-line

# Up/Down before history-substring-search is loaded
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey '^[[A' up-line-or-beginning-search '^[OA' up-line-or-beginning-search
bindkey '^[[B' down-line-or-beginning-search '^[OB' down-line-or-beginning-search

zstyle ':completion:*' menu no
zstyle ':completion:*:git-checkout:*' sort false
zstyle ':completion:*:descriptions' format '[%d]'
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
zstyle ':fzf-tab:*' switch-group ',' '.'

ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_MANUAL_REBIND=1

# Paste support for the prompt character (undollar covers `$ `)
'❯'() { "$@" }

typeset -g SPIKE_CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/spike

# Source the output of `cmd...`, regenerated when the binary is newer than the cache.
spike_cache_eval() {
  local name=$1; shift
  local bin=${commands[$1]} f=$SPIKE_CACHE/$name.zsh
  [[ -n $bin ]] || return 0
  if [[ ! -s $f || $bin -nt $f ]]; then
    mkdir -p -- $SPIKE_CACHE
    "$@" >| $f || return
    zcompile -R -- $f.zwc $f
  fi
  source $f
}

spike_compinit() {
  autoload -Uz compinit
  local d=$SPIKE_CACHE/zcompdump
  mkdir -p -- $SPIKE_CACHE
  if [[ -n $d(#qN.mh+24) || ! -s $d ]]; then
    compinit -d $d
  else
    compinit -C -d $d
  fi
  [[ $d.zwc -nt $d ]] || zcompile -R -- $d.zwc $d
}

# LS_COLORS from the trapd00r/LS_COLORS database file given as $1
spike_lscolors() {
  local src=$1 f=$SPIKE_CACHE/lscolors.zsh
  [[ -r $src ]] || return 0
  if [[ ! -s $f || $src -nt $f ]]; then
    mkdir -p -- $SPIKE_CACHE
    dircolors -b $src >| $f
  fi
  source $f
  zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
}

# Tool integrations, after compinit
spike_tools() {
  spike_cache_eval fzf fzf --zsh
  spike_cache_eval zoxide zoxide init zsh
}

spike_after_autosuggest() {
  bindkey '^ ' autosuggest-accept
  bindkey '^_' autosuggest-execute
}

spike_after_hss() {
  local km
  for km in emacs viins vicmd; do
    bindkey -M $km '^[[A' history-substring-search-up '^[OA' history-substring-search-up
    bindkey -M $km '^[[B' history-substring-search-down '^[OB' history-substring-search-down
  done
}

source ~/.zsh/spike-marker.zsh
