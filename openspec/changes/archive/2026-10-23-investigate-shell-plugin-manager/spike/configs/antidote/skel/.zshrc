# Candidate: antidote + zsh-defer, rebuilt from the feature list.
ANTIDOTE_HOME=${XDG_CACHE_HOME:-$HOME/.cache}/antidote
[[ -d ~/.antidote ]] || git clone -q --depth 1 https://github.com/mattmc3/antidote ~/.antidote

source ~/.zsh/common.zsh
spike_cache_eval starship starship init zsh --print-full-init

# Friendly paths ($ANTIDOTE_HOME/owner/repo); no precmd/reset-prompt after every deferred plugin.
zstyle ':antidote:bundle' use-friendly-names on
zstyle ':antidote:bundle:*' defer-options '-dmpr'

# pre: runs synchronously, so it queues the init step in front of fzf-tab.
spike_defer_init() {
  zsh-defer -dmpr -c 'spike_lscolors $ANTIDOTE_HOME/trapd00r/LS_COLORS/LS_COLORS; spike_compinit; spike_tools'
}
spike_post_autosuggest() { _zsh_autosuggest_start; spike_after_autosuggest }

# Static file is regenerated only when .zsh_plugins.txt changes.
source ~/.antidote/antidote.zsh
antidote load
