alias zshheys="nano $0"


# in plugins the following is done when loading zsh-autosuggestions
    # Bind Ctrl+_ to execute the autosuggestion
    # bindkey '^_' autosuggest-execute
    # Bind Ctrl+Space to accept the autosuggestion
    # bindkey '^ ' autosuggest-accept

# Bind the delete key to delete the character under the cursor
bindkey "^[[3~" delete-char
# Bind the Home/End key to move the cursor to the beginning/end of the line
bindkey "^[[H" beginning-of-line
bindkey "^[[F" end-of-line

# Bind the Up/down arrow key to search the command history for a command that matches the current input
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

# Bind the Right/Left arrow key to move the cursor forward one character
bindkey "^[[C" forward-char
bindkey "^[[D" backward-char
