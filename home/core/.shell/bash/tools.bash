# Helpers are removed again at the end of the file.

# Puts directory $1 in front of PATH if it exists and is not in PATH yet.
_dotfiles_path_prepend() {
    [ -d "$1" ] || return 0
    case ":$PATH:" in
        *":$1:"*) ;;
        *) PATH="$1:$PATH" ;;
    esac
}

# True if the LS_COLORS cache $1 is missing or older than its source $2.
_dotfiles_lscolors_stale() {
    [ ! -s "$1" ] || [ "$2" -nt "$1" ]
}

# Loads LS_COLORS from the dircolors file $1 through a cached `dircolors -b` result.
_dotfiles_load_lscolors() {
    local cache
    [ -r "$1" ] || return 0
    command -v dircolors >/dev/null 2>&1 || return 0
    cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/lscolors.bash"
    if _dotfiles_lscolors_stale "$cache" "$1"; then
        mkdir -p "${cache%/*}" && dircolors -b "$1" >"$cache"
    fi
    # shellcheck source=/dev/null
    . "$cache"
}

# Keep mise shims visible before shell activation and env-file loading.
_dotfiles_path_prepend "$HOME/.local/bin"
if command -v mise >/dev/null 2>&1; then
    eval "$(mise activate bash)"
fi

if command -v machine >/dev/null 2>&1; then
    eval "$(machine completion bash 2>/dev/null)"
fi

_dotfiles_plugins="${XDG_DATA_HOME:-$HOME/.local/share}/antidote"
for _dotfiles_dir in paulirish/git-open paulirish/git-recent Fakerr/git-recall; do
    _dotfiles_path_prepend "$_dotfiles_plugins/$_dotfiles_dir"
done
_dotfiles_load_lscolors "$_dotfiles_plugins/trapd00r/LS_COLORS/LS_COLORS"
unset _dotfiles_plugins _dotfiles_dir _dotfiles_lscolors
LS_COLORS=$LS_COLORS:'di=0;32'
export LS_COLORS

if declare -F dotfiles_cache_eval >/dev/null; then
    dotfiles_cache_eval fzf fzf --bash
    dotfiles_cache_eval zoxide zoxide init bash
    dotfiles_cache_eval copilot copilot completion bash
    dotfiles_cache_eval zellij zellij setup --generate-completion bash
    dotfiles_cache_eval opencode opencode --completions bash
    dotfiles_cache_eval uv uv generate-shell-completion bash
    dotfiles_cache_eval mise mise completion bash
    dotfiles_cache_eval lazygit lazygit completion bash
    dotfiles_cache_eval openspec openspec completion generate bash
    dotfiles_cache_eval starship-completion starship completions bash
fi
# bw (Bitwarden CLI) generates zsh completion only; none for Bash.
if declare -F dotfiles_cache_eval >/dev/null && declare -F _get_comp_words_by_ref >/dev/null 2>&1; then
    complete -p gh >/dev/null 2>&1 || dotfiles_cache_eval gh gh completion -s bash
    dotfiles_cache_eval git-lfs git-lfs completion bash
    dotfiles_cache_eval tailscale tailscale completion bash
    dotfiles_cache_eval dms dms completion bash
fi
unset -f _dotfiles_path_prepend _dotfiles_lscolors_stale _dotfiles_load_lscolors
