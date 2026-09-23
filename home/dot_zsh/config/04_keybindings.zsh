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

# Bind Up/Down to prefix history search.
# Some terminals send ^[[A/^[[B, others ^[OA/^[OB (application cursor mode).
# This function is intentionally called twice:
# - once now (fallback may be used if plugin is not loaded yet),
# - again via zinit atload hook once history-substring-search is available.
function _history_substring_search_config() {
    if (( $+widgets[history-substring-search-up] && $+widgets[history-substring-search-down] )); then
        for keymap in emacs viins vicmd; do
            bindkey -M "$keymap" '^[[A' history-substring-search-up
            bindkey -M "$keymap" '^[[B' history-substring-search-down
            bindkey -M "$keymap" '^[OA' history-substring-search-up
            bindkey -M "$keymap" '^[OB' history-substring-search-down
        done
    else
        autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
        zle -N up-line-or-beginning-search
        zle -N down-line-or-beginning-search
        for keymap in emacs viins vicmd; do
            bindkey -M "$keymap" '^[[A' up-line-or-beginning-search
            bindkey -M "$keymap" '^[[B' down-line-or-beginning-search
            bindkey -M "$keymap" '^[OA' up-line-or-beginning-search
            bindkey -M "$keymap" '^[OB' down-line-or-beginning-search
        done
    fi
}

_history_substring_search_config

# Bind the Right/Left arrow key to move the cursor forward one character
bindkey "^[[C" forward-char
bindkey "^[[D" backward-char
