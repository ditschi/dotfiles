# shellcheck shell=bash
# Cached tool init output, sourced by the explicit zsh and Bash loaders.
# `dotfiles_cache_eval <name> <cmd> [args...]` sources the output of the command, which is
# regenerated only when the tool binary is newer than the cache file. A missing tool is skipped.
dotfiles_cache_eval() {
    local name="$1" bin file shell_ext=bash
    shift
    if [ -n "${ZSH_VERSION:-}" ]; then
        shell_ext=zsh
        # shellcheck disable=SC2154 # $commands is zsh's command hash table
        bin=${commands[$1]}
    else
        bin=$(type -P "$1")
    fi
    [ -n "$bin" ] || return 0
    file="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/$name.$shell_ext"
    if [ ! -s "$file" ] || [ "$bin" -nt "$file" ]; then
        mkdir -p "${file%/*}"
        "$@" >|"$file" 2>/dev/null || {
            rm -f "$file"
            return 0
        }
    fi
    # shellcheck source=/dev/null
    . "$file"
}
