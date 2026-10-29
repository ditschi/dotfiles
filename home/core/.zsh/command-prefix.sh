# shellcheck shell=bash
dotfiles_command_prefix() {
    if [ -n "${ZSH_VERSION:-}" ]; then
        emulate -L ksh
    fi
    local remaining=$1 word prefix_length word_index matches
    local -a words=() tails=()
    DOTFILES_COMMAND_PREFIX_SUGGESTION=''
    case "$remaining" in
        *[!a-zA-Z0-9_./,:@%+\ $'\t'-]* | '') return 1 ;;
    esac
    while [[ -n $remaining ]]; do
        while [[ $remaining == [[:blank:]]* ]]; do
            remaining=${remaining#?}
        done
        [[ -n $remaining ]] || break
        tails+=("$remaining")
        word=${remaining%%[[:blank:]]*}
        words+=("$word")
        remaining=${remaining#"$word"}
    done
    for ((prefix_length = ${#words[@]} / 2; prefix_length > 0; prefix_length--)); do
        matches=1
        for ((word_index = 0; word_index < prefix_length; word_index++)); do
            if [[ ${words[word_index]} != "${words[word_index + prefix_length]}" ]]; then
                matches=0
                break
            fi
        done
        if ((matches)); then
            # shellcheck disable=SC2034
            DOTFILES_COMMAND_PREFIX_SUGGESTION=${tails[prefix_length]}
            return 0
        fi
    done
    return 1
}
