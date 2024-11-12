alias zshhistory="nano $0"

export HISTFILE=~/.shared_history
export HISTSIZE=50000
export SAVEHIST=60000 # recommended value 1.2 * SAVEHIST
export HISTTIMEFORMAT="[%F %T] "

if [ -n "$ZSH_VERSION" ]; then
    # running in Zsh
    setopt extended_history       # record timestamp of command in HISTFILE
    setopt hist_verify            # show command with history expansion to user before running it
    setopt hist_expire_dups_first # delete duplicates first when HISTFILE size exceeds HISTSIZE
    setopt hist_ignore_space      # ignore commands that start with space
    setopt hist_find_no_dups
    setopt share_history # share command history data
    # following should be turned off, if sharing history via setopt SHARE_HISTORY
    unsetopt inc_append_history
elif [ -n "$BASH_VERSION" ]; then
    # running in bash
    # append to the history file, don't overwrite it
    shopt -s histappend
    # don't put duplicate lines or lines starting with space in the history.
    # See bash(1) for more options
    export HISTCONTROL=ignoredups:ignorespace
    PROMPT_COMMAND="history -a; history -r; $PROMPT_COMMAND"
fi
