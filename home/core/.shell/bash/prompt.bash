# Starship wraps this PROMPT_COMMAND and preserves mise's prompt hook.
PROMPT_COMMAND='history -a;history -r'
declare -F _dotfiles_prefix_precmd >/dev/null && PROMPT_COMMAND="_dotfiles_prefix_precmd;$PROMPT_COMMAND"
declare -F _mise_hook_prompt_command >/dev/null && PROMPT_COMMAND="_mise_hook_prompt_command;$PROMPT_COMMAND"
declare -F dotfiles_update_prompt >/dev/null && PROMPT_COMMAND="$PROMPT_COMMAND;dotfiles_update_prompt"

dotfiles_prompt_state() {
    unset DOTFILES_PROMPT_ZSH DOTFILES_PROMPT_ZSH_ERR DOTFILES_PROMPT_BASH DOTFILES_PROMPT_BASH_ERR
    if [[ ${STARSHIP_CMD_STATUS:-0} == 0 ]]; then
        export DOTFILES_PROMPT_BASH=1
    else
        export DOTFILES_PROMPT_BASH_ERR=1
    fi
}
PROMPT_COMMAND="$PROMPT_COMMAND;dotfiles_prompt_state"

declare -F dotfiles_cache_eval >/dev/null && dotfiles_cache_eval starship-init starship init bash --print-full-init
if ! declare -F starship_precmd >/dev/null; then
    debian_chroot=${debian_chroot:-}
    PS1='${DOTFILES_UPDATE_SEGMENT:+$DOTFILES_UPDATE_SEGMENT }${DOTFILES_DISK_SEGMENT:+$DOTFILES_DISK_SEGMENT }${debian_chroot:+($debian_chroot)}\[\033[01;34m\]\w\[\033[00m\] \[\033[01;35m\]❯\[\033[00m\] '
    case "$TERM" in
        xterm* | rxvt*) PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1" ;;
    esac
fi
