# shellcheck shell=bash
# The helpers run inside dotfiles_command_prefix (zsh: with its ksh emulation) and fill
# or read its local arrays `words` and `tails`.

# Splits $1 at blanks into words and tails (the rest of the line from each word on).
_dotfiles_command_prefix_split() {
    local remaining=$1 word
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
}

# True if the first $1 words are repeated right after themselves.
_dotfiles_command_prefix_repeats() {
    local length=$1 word_index
    for ((word_index = 0; word_index < length; word_index++)); do
        [[ ${words[word_index]} == "${words[word_index + length]}" ]] || return 1
    done
    return 0
}

dotfiles_command_prefix() {
    if [ -n "${ZSH_VERSION:-}" ]; then
        emulate -L ksh
    fi
    local prefix_length
    local -a words=() tails=()
    DOTFILES_COMMAND_PREFIX_SUGGESTION=''
    case "$1" in
        *[!a-zA-Z0-9_./,:@%+\ $'\t'-]* | '') return 1 ;;
    esac
    _dotfiles_command_prefix_split "$1"
    for ((prefix_length = ${#words[@]} / 2; prefix_length > 0; prefix_length--)); do
        _dotfiles_command_prefix_repeats "$prefix_length" || continue
        # shellcheck disable=SC2034
        DOTFILES_COMMAND_PREFIX_SUGGESTION=${tails[prefix_length]}
        return 0
    done
    return 1
}
