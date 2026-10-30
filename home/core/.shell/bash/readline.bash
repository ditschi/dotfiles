bind '"\e[A": history-search-backward' '"\e[B": history-search-forward'
bind '"\eOA": history-search-backward' '"\eOB": history-search-forward'
_dotfiles_sudo_command_line() {
    if [ -z "$READLINE_LINE" ]; then
        READLINE_LINE=$(fc -ln -1 2>/dev/null)
        READLINE_LINE=${READLINE_LINE#"${READLINE_LINE%%[![:space:]]*}"}
    fi
    if [ "${READLINE_LINE#sudo }" != "$READLINE_LINE" ]; then
        READLINE_LINE=${READLINE_LINE#sudo }
    else
        READLINE_LINE="sudo $READLINE_LINE"
    fi
    READLINE_POINT=${#READLINE_LINE}
}
bind -x '"\e\e": _dotfiles_sudo_command_line'

eval '❯() { "$@"; }'
if declare -F command_not_found_handle >/dev/null; then
    eval "_dotfiles_command_not_found_handle()$(declare -f command_not_found_handle | tail -n +2)"
fi
command_not_found_handle() {
    if [ "$1" = '$' ]; then
        shift
        "$@"
        return
    fi
    if declare -F _dotfiles_command_not_found_handle >/dev/null; then
        _dotfiles_command_not_found_handle "$@"
        return
    fi
    printf 'bash: %s: command not found\n' "$1" >&2
    return 127
}

if [ -r "$HOME/.shell/common/command-prefix.sh" ]; then
    . "$HOME/.shell/common/command-prefix.sh"
    _dotfiles_prefix_capture() {
        _dotfiles_prefix_line=$READLINE_LINE
        _dotfiles_prefix_pending=''
    }
    _dotfiles_prefix_precmd() {
        local command_status=$?
        if declare -F starship_precmd >/dev/null; then
            command_status=${STARSHIP_CMD_STATUS:-$command_status}
        fi
        _dotfiles_prefix_status=$command_status
        _dotfiles_prefix_pending=''
        if ((command_status)) && dotfiles_command_prefix "${_dotfiles_prefix_line:-}"; then
            _dotfiles_prefix_pending=$DOTFILES_COMMAND_PREFIX_SUGGESTION
        fi
        _dotfiles_prefix_line=''
        return "$command_status"
    }
    _dotfiles_prefix_insert() {
        if [[ -z $READLINE_LINE ]] && ! read -r -t 0; then
            READLINE_LINE=${_dotfiles_prefix_pending:-}
            READLINE_POINT=${#READLINE_LINE}
        fi
        _dotfiles_prefix_pending=''
    }
    _dotfiles_prefix_bind() {
        local keymap binding sequence
        for keymap in emacs-standard vi-insert vi-command; do
            while IFS= read -r binding; do
                case "$binding" in
                    *': accept-line')
                        sequence=${binding%: accept-line}
                        [[ $sequence == '"\C-x\C-a"' ]] && continue
                        bind -m "$keymap" "$sequence: \"\\C-x\\C-c\\C-x\\C-a\\C-x\\C-i\""
                        ;;
                esac
            done < <(bind -m "$keymap" -p)
            bind -m "$keymap" '"\C-x\C-a": accept-line'
            bind -m "$keymap" -x '"\C-x\C-c": _dotfiles_prefix_capture'
            bind -m "$keymap" -x '"\C-x\C-i": _dotfiles_prefix_insert'
        done
    }
    _dotfiles_prefix_bind
fi
