# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

SCRIPTDIR=$(dirname "$0")

# If not running interactively, don't do anything
case $- in
    *i*) ;;
    *) return ;;
esac

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color | *-256color) color_prompt=yes ;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
        # We have color support; assume it's compliant with Ecma-48
        # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
        # a case would tend to support setf rather than setaf.)
        color_prompt=yes
    else
        color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
    xterm* | rxvt*)
        PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
        ;;
    *) ;;
esac

export GIT_PS1_SHOWCONFLICTSTATE=yes
source /usr/lib/git-core/git-sh-prompt
source /usr/share/bash-completion/completions/git

# Add git branch to commandline
parse_git_branch() {
    git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}
export PS1="\u@\h \[\e[32m\]\w \[\e[91m\]\$(parse_git_branch)\[\e[00m\]$ "

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

DOTFILES_DIR="/home/$(whoami)/dotfiles/.zsh/config"
if [ -d "$DOTFILES_DIR" ]; then
    echo "Loading customization from $DOTFILES_DIR"

    . "$DOTFILES_DIR/00_alias.zsh"
    . "$DOTFILES_DIR/01_env.zsh"
    . "$DOTFILES_DIR/05_pyenv.zsh"
    . "$DOTFILES_DIR/06_history.zsh"

    unset WORK_SETUP
    if [[ $(whoami) =~ (^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$) ]]; then
        export WORK_SETUP="true"
        . "$DOTFILES_DIR/01_work_tools.zsh"
        . "$DOTFILES_DIR/01_work.zsh"
    fi
else
    echo "Could not find dotfiles directory: $DOTFILES_DIR"
fi

echo ""
echo -e "\033[0;33m\e[1mInstall dotfile setup to use zsh ;)\033[0m\e[21m"
echo -e "\033[0;32m\e[1m  python3 \"$SCRIPTDIR/install.py\" && zsh \033[0m\e[21m"

## <!-- BEGIN ANSIBLE MANAGED BLOCK - update colors -->
if [ "$color_prompt" = yes ]; then
  PS1='${debian_chroot:+($debian_chroot)}[\033[01;32m]\u@\h[\033[00m]:[\033[0;32m]\w[\033[00m]\$'
fi
LS_COLORS=$LS_COLORS:'di=0;32' ; export LS_COLORS
export PROMPT_COMMAND='history -a;history -r'
## <!-- END ANSIBLE MANAGED BLOCK - update colors -->

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
