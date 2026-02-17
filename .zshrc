# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# If you come from bash you might have to change your $PATH.
export PATH=$HOME/bin:/usr/local/bin:$PATH
alias zshconfig="nano ~/.zshrc"

# Use emacs keybindings even if our EDITOR is set to vi
bindkey -e

ENABLE_CORRECTION="true"

### Added by Zinit's installer
ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
[ ! -d $ZINIT_HOME ] && mkdir -p "$(dirname $ZINIT_HOME)"
[ ! -d $ZINIT_HOME/.git ] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME" \
     && print -P "%F{220}${bold}Please ensure the default packages are installed:%f${normal}" \
     && print -P "%F{33}  sudo apt install autojump fonts-powerline fonts-firacode fzf%f"
source "${ZINIT_HOME}/zinit.zsh"


autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit
### End of Zinit's installer chunk


# cheheck for dofile update
if [ -d ~/dotfiles ]; then
    pushd ~/dotfiles > /dev/null
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    git fetch
    if [ $(git rev-list --count HEAD..origin/$current_branch) -gt 0 ]; then
        echo "Hint: There are updates for dotfiles available."
    fi
    popd > /dev/null
fi

export ZSH=~/.zsh
# Requirements:
#  sudo apt install zsh git wget autojump fzf fonts-powerline fonts-firacode
source $ZSH/config/00_LOADER.zsh

if [ -f "$HOME/.dotfiles-update-available" ]; then
    echo "Hint: Dotfiles update available (run: dotfiles-update-apply)"
fi

# Local zshrc extension point
[[ ! -f ~/.zshrc-local ]] || source ~/.zshrc-local

# Quiet startup: container detection is kept implicit.
