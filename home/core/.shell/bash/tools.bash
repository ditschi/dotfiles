# Keep mise shims visible before shell activation and env-file loading.
if [ -d "$HOME/.local/bin" ]; then
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) ;;
        *) PATH="$HOME/.local/bin:$PATH" ;;
    esac
fi
if command -v mise >/dev/null 2>&1; then
    eval "$(mise activate bash)"
fi

if command -v machine >/dev/null 2>&1; then
    eval "$(machine completion bash 2>/dev/null)"
fi

_dotfiles_plugins="${XDG_DATA_HOME:-$HOME/.local/share}/antidote"
for _dotfiles_dir in paulirish/git-open paulirish/git-recent Fakerr/git-recall; do
    if [ -d "$_dotfiles_plugins/$_dotfiles_dir" ]; then
        case ":$PATH:" in
            *":$_dotfiles_plugins/$_dotfiles_dir:"*) ;;
            *) PATH="$_dotfiles_plugins/$_dotfiles_dir:$PATH" ;;
        esac
    fi
done
if [ -r "$_dotfiles_plugins/trapd00r/LS_COLORS/LS_COLORS" ] && command -v dircolors >/dev/null 2>&1; then
    _dotfiles_lscolors="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/lscolors.bash"
    if [ ! -s "$_dotfiles_lscolors" ] || [ "$_dotfiles_plugins/trapd00r/LS_COLORS/LS_COLORS" -nt "$_dotfiles_lscolors" ]; then
        mkdir -p "${_dotfiles_lscolors%/*}" && dircolors -b "$_dotfiles_plugins/trapd00r/LS_COLORS/LS_COLORS" >"$_dotfiles_lscolors"
    fi
    # shellcheck source=/dev/null
    . "$_dotfiles_lscolors"
fi
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
    if declare -F _get_comp_words_by_ref >/dev/null 2>&1; then
        if ! complete -p gh >/dev/null 2>&1; then
            dotfiles_cache_eval gh gh completion -s bash
        fi
        dotfiles_cache_eval git-lfs git-lfs completion bash
    fi
fi
