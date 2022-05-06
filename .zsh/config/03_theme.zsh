

# source $ZSH/themes/powerlevel10k/powerlevel10k.zsh-theme
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
zinit ice wait'!' lucid atload'[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh; _p9k_precmd' nocd
zinit light romkatv/powerlevel10k


zinit ice atclone"dircolors -b LS_COLORS > clrs.zsh" \
    atpull'%atclone' pick"clrs.zsh" nocompile'!' \
    atload'zstyle ":completion:*" list-colors "${(s.:.)LS_COLORS}"'
zinit light trapd00r/LS_COLORS
