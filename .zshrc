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
if [[ ! -f $HOME/.local/share/zinit/zinit.git/zinit.zsh ]]; then
    print -P "%F{33} %F{220}Installing %F{33}ZDHARMA-CONTINUUM%F{220} Initiative Plugin Manager (%F{33}zdharma-continuum/zinit%F{220}...%f"
    command mkdir -p "$HOME/.local/share/zinit" && command chmod g-rwX "$HOME/.local/share/zinit"
    command git clone https://github.com/zdharma-continuum/zinit "$HOME/.local/share/zinit/zinit.git" && \
        print -P "%F{33} %F{34}Installation successful.%f%b" || \
        print -P "%F{160} The clone has failed.%f%b"
    print ""
    print -P "%F{220}${bold}Please ensure the default packages are installed:%f${normal}"
    print -P "%F{33}  sudo apt install autojump fonts-powerline fonts-firacode fzf%f"
fi

source "$HOME/.local/share/zinit/zinit.git/zinit.zsh"
autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit

# Load a few important annexes, without Turbo
# (this is currently required for annexes)
zinit light-mode for \
    zdharma-continuum/zinit-annex-as-monitor \
    zdharma-continuum/zinit-annex-bin-gem-node \
    zdharma-continuum/zinit-annex-patch-dl \
    zdharma-continuum/zinit-annex-rust

### End of Zinit's installer chunk


# load customisation
[[ ! -f ~/.env ]] || source ~/.env

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
