alias zshtheme="nano $ZSH/config/03_theme.zsh"

# custom prompt symbol when running in docker container
# to use this add 'dockerenv' to POWERLEVEL9K_LEFT_PROMPT_ELEMENTS in ~/.p10k.zsh (e.g. before prompt_char)
function prompt_dockerenv() {
    if [ -f /.dockerenv ]; then
        p10k segment -i '🐳'
    fi
}

# load powerlevel10k config and plugin
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
zinit ice depth=1; zinit light romkatv/powerlevel10k

zinit ice atclone"dircolors -b LS_COLORS > clrs.zsh" \
    atpull'%atclone' pick"clrs.zsh" nocompile'!' \
    atload'zstyle ":completion:*" list-colors "${(s.:.)LS_COLORS}"'
zinit light trapd00r/LS_COLORS
