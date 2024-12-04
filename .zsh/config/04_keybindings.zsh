alias zshheys="nano $0"

bindkey "^[[3~" delete-char
bindkey "^[[H" beginning-of-line
bindkey "^[[F" end-of-line

bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down
# bindkey "^[[A" up-line-or-history
# bindkey "^[[B" down-line-or-history
bindkey "^[[C" forward-char
bindkey "^[[D" backward-char

bindkey "^[[5~" beginning-of-buffer
bindkey "^[[6~" end-of-buffer
