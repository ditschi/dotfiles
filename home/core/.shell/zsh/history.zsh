alias zshhistory="nano $HOME/.shell/zsh/history.zsh"

export HISTSIZE=60000
export SAVEHIST=50000
export HISTFILE=~/.zsh_history

unsetopt extended_history
setopt share_history
setopt append_history
setopt inc_append_history
setopt hist_ignore_all_dups
setopt hist_ignore_dups
setopt hist_verify
setopt hist_ignore_space
setopt hist_reduce_blanks
setopt hist_save_no_dups
setopt hist_find_no_dups
setopt hist_no_store
