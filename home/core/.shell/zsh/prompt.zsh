alias zshtheme="nano $0"

# Prompt: Starship (~/.config/starship.toml, shared with bash) when installed, else a built-in one.
# The update state (update-state.sh) reaches Starship through the exported
# DOTFILES_UPDATE_SEGMENT (env_var module); reading the state file uses builtins only.
function _dotfiles_update_segment() {
    dotfiles_update_prompt
}
precmd_functions+=(_dotfiles_update_segment)

dotfiles_cache_eval starship starship init zsh --print-full-init
# Prompt character colour: shell + last exit status (env_var.prompt_* in starship.toml).
# Runs after Starship's precmd, which has set STARSHIP_CMD_STATUS.
function _dotfiles_prompt_state() {
    unset DOTFILES_PROMPT_ZSH DOTFILES_PROMPT_ZSH_ERR DOTFILES_PROMPT_BASH DOTFILES_PROMPT_BASH_ERR
    if [[ ${STARSHIP_CMD_STATUS:-0} == 0 ]]; then
        export DOTFILES_PROMPT_ZSH=1
    else
        export DOTFILES_PROMPT_ZSH_ERR=1
    fi
}
(( $+functions[prompt_starship_precmd] )) && precmd_functions+=(_dotfiles_prompt_state)
# Built-in prompt when Starship is missing or its init failed.
if (( ! $+functions[prompt_starship_precmd] )); then
    PROMPT='%F{blue}%3~%f %F{green}❯%f '
    function _dotfiles_update_rprompt() {
        RPROMPT=""
        [[ -z $DOTFILES_UPDATE_SEGMENT ]] || RPROMPT="%F{214}${DOTFILES_UPDATE_SEGMENT}%f"
        [[ -z $DOTFILES_DISK_SEGMENT ]] || RPROMPT+="${RPROMPT:+ }%F{red}${DOTFILES_DISK_SEGMENT}%f"
    }
    precmd_functions+=(_dotfiles_update_rprompt)
fi
