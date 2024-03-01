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

export HISTFILE=~/.zsh_history
export HISTSIZE=50000
export SAVEHIST=60000     # Zsh recommended value 1.2 * SAVEHIST
export HISTTIMEFORMAT="[%F %T] "
setopt extended_history       # record timestamp of command in HISTFILE
setopt hist_verify            # show command with history expansion to user before running it
setopt hist_expire_dups_first # delete duplicates first when HISTFILE size exceeds HISTSIZE
setopt hist_ignore_space      # ignore commands that start with space
setopt hist_find_no_dups
setopt share_history          # share command history data
# following should be turned off, if sharing history via setopt SHARE_HISTORY
#setopt inc_append_history
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


# load customisation
[[ ! -f ~/.env ]] || source ~/.env

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

# Local zshrc extension point
[[ ! -f ~/.zshrc-local ]] || source ~/.zshrc-local

if [ -f /.dockerenv ]; then
    echo "Running inside a container!";
else
    # echo "Runing in the host machine!";
fi
