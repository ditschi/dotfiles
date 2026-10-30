source "$HOME/.shell/zsh/init.zsh"

dotfiles_update_startup

# Local zshrc extension point
[[ ! -f ~/.zshrc-local ]] || source ~/.zshrc-local
