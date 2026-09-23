alias zshtheme="nano $0"

# custom prompt symbol when running in docker container
# to use this add 'dockerenv' to POWERLEVEL9K_LEFT_PROMPT_ELEMENTS in ~/.p10k.zsh (e.g. before prompt_char)
function prompt_dockerenv() {
    if [ -f /.dockerenv ]; then
        p10k segment -i '🐳'
    fi
}

# load powerlevel10k config and plugin (zsh prompt)
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
zinit ice depth="1"
zinit light romkatv/powerlevel10k
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Load LS_COLORS plugin
zinit pack for ls_colors

# Ensure zsh-syntax-highlighting is loaded last
zinit light zsh-users/zsh-syntax-highlighting
