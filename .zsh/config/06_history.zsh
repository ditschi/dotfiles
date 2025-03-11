alias zshhistory="nano $0"

export HISTFILE=~/.shared_history
export HISTSIZE=50000
export SAVEHIST=60000 # recommended value 1.2 * SAVEHIST

if [ -n "$BASH_VERSION" ]; then
    # bash-specific settings
    shopt -s histappend                 # Append to the history file, don't overwrite
    export HISTIGNORE="&:[ ]*:#*"       # Ignore duplicates (&), space-only commands, and comments (#)
    HISTCONTROL=ignoredups:ignorespace  # Ignorespace and ignoredups
    PROMPT_COMMAND="history -a; history -c; history -n; history -r; $PROMPT_COMMAND" # Sync history between sessions
    export HISTTIMEFORMAT='(%Y-%m-%d) (%H:%M:%S) '
elif [ -n "$ZSH_VERSION" ]; then
    # zsh-specific settings
    unsetopt extended_history          # Disable extended history for Bash-like behavior
    setopt hist_verify                 # Show expanded command before execution
    setopt hist_ignore_space           # Ignore commands starting with space
    setopt hist_reduce_blanks          # Remove extra blanks in commands
    setopt hist_save_no_dups           # Avoid saving duplicate entries
    setopt share_history               # Share history across sessions
    setopt append_history              # Append to the history file, don't overwrite
    setopt inc_append_history          # Write to the history file immediately
    setopt hist_ignore_all_dups        # Ignore duplicate commands
else
    echo "Unsupported shell. Shared history setup may not work."
fi
