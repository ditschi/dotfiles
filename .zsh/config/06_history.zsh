alias zshhistory="nano $0"

# export HISTFILE=~/.shared_history
export HISTSIZE=60000 # recommended value 1.2 * SAVEHIST
export SAVEHIST=50000

if [ -n "$BASH_VERSION" ]; then
    # bash-specific settings
    export HISTFILE=~/.bash_history
    shopt -s histappend                 # Append to the history file, don't overwrite
    shopt -s cdspell dirspell           # Correct minor typos in cd paths
    export HISTIGNORE="&:[ ]*:#*"       # Ignore duplicates (&), space-only commands, and comments (#)
    HISTCONTROL=ignoredups:ignorespace  # Ignorespace and ignoredups
    PROMPT_COMMAND="history -a; history -c; history -n; history -r; $PROMPT_COMMAND" # Sync history between sessions
    export HISTTIMEFORMAT='(%Y-%m-%d) (%H:%M:%S) '

    # Prefix-aware history search with Up/Down (uses current input as filter).
    # Support both common arrow sequences and application cursor mode.
    bind '"\e[A": history-search-backward'
    bind '"\e[B": history-search-forward'
    bind '"\eOA": history-search-backward'
    bind '"\eOB": history-search-forward'

    # Align basic cursor/editing keys with common zsh behavior.
    bind '"\e[H": beginning-of-line'
    bind '"\e[F": end-of-line'
    bind '"\eOH": beginning-of-line'
    bind '"\eOF": end-of-line'
    bind '"\e[3~": delete-char'
elif [ -n "$ZSH_VERSION" ]; then
    # zsh-specific settings
    export HISTFILE=~/.zsh_history

    unsetopt extended_history          # Don't save timestamps in extended format
    setopt share_history             # Don't use share_history (it forces extended format)
    setopt append_history              # Append to the history file, don't overwrite
    setopt inc_append_history          # Write to the history file immediately
    setopt hist_ignore_all_dups        # Ignore duplicate commands
    setopt hist_ignore_dups            # Ignore consecutive duplicates
    setopt hist_verify                 # Show expanded command before execution
    setopt hist_ignore_space           # Ignore commands starting with space
    setopt hist_reduce_blanks          # Remove extra blanks in commands
    setopt hist_save_no_dups           # Avoid saving duplicate entries
    setopt hist_find_no_dups           # Don't show duplicates when searching
    setopt hist_no_store               # Don't store history/fc commands
else
    echo "Unsupported shell. Shared history setup may not work."
fi
