# If you come from bash you might have to change your $PATH.
export PATH=$HOME/bin:/usr/local/bin:$PATH
alias zshconfig="nano ~/.zshrc"

# Use emacs keybindings even if our EDITOR is set to vi
bindkey -e

# Offer a correction for mistyped commands (gti -> git).
setopt correct

# Own completion functions; compinit runs once, deferred (see ~/.zsh/config/02_plugins.zsh).
fpath+=~/.zfunc

export ZSH=~/.zsh
source $ZSH/config/00_LOADER.zsh

dotfiles_update_startup

# Local zshrc extension point
[[ ! -f ~/.zshrc-local ]] || source ~/.zshrc-local
