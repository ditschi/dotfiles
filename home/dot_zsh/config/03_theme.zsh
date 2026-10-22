alias zshtheme="nano $0"

# custom prompt symbol when running in docker container
# to use this add 'dockerenv' to POWERLEVEL9K_LEFT_PROMPT_ELEMENTS in ~/.p10k.zsh (e.g. before prompt_char)
function prompt_dockerenv() {
    if [ -f /.dockerenv ]; then
        p10k segment -i '🐳'
    fi
}

# Update state segment for ~/.p10k.zsh (add 'dotfiles_update' to POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS).
# Reading the state file uses builtins only, so this stays cheap on every prompt.
function prompt_dotfiles_update() {
    dotfiles_update_prompt
    case "$DOTFILES_UPDATE_SEGMENT_KIND" in
        attention) p10k segment -f 196 -t "$DOTFILES_UPDATE_SEGMENT" ;;
        available) p10k segment -f 214 -t "$DOTFILES_UPDATE_SEGMENT" ;;
        reload) p10k segment -f 39 -t "$DOTFILES_UPDATE_SEGMENT" ;;
    esac
}

# Without ~/.p10k.zsh (profiles rpi-zero and container) show the state at the right of the prompt.
if [[ ! -f ~/.p10k.zsh ]]; then
    function _dotfiles_update_rprompt() {
        dotfiles_update_prompt
        RPROMPT=""
        [[ -z $DOTFILES_UPDATE_SEGMENT ]] || RPROMPT="%F{214}${DOTFILES_UPDATE_SEGMENT}%f"
    }
    precmd_functions+=(_dotfiles_update_rprompt)
fi

# load powerlevel10k config and plugin (zsh prompt)
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
zinit ice depth="1"
zinit light romkatv/powerlevel10k
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Load LS_COLORS plugin
zinit pack for ls_colors

# Ensure zsh-syntax-highlighting is loaded last
zinit light zsh-users/zsh-syntax-highlighting
