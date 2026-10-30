# shellcheck shell=bash
export PATH="$PATH:$HOME/.local/bin"

# VS Code's copilotCLIShim drops its dir from PATH by literal match on its realpath;
# a symlinked $HOME would otherwise make it start itself recursively.
if [[ $PATH == */github.copilot-chat/copilotCli* ]]; then
    _dotfiles_rest=$PATH: _dotfiles_path=
    while [[ -n $_dotfiles_rest ]]; do
        _dotfiles_dir=${_dotfiles_rest%%:*}
        _dotfiles_rest=${_dotfiles_rest#*:}
        if [[ $_dotfiles_dir == /*/github.copilot-chat/copilotCli && -d $_dotfiles_dir ]]; then
            # shellcheck disable=SC2034 # Keeps zsh chpwd hooks (zoxide) quiet in the subshell.
            _dotfiles_real=$(chpwd_functions=() && cd -P -- "$_dotfiles_dir" && pwd -P) &&
                _dotfiles_dir=$_dotfiles_real
        fi
        _dotfiles_path+=:$_dotfiles_dir
    done
    export PATH=${_dotfiles_path#:}
    unset _dotfiles_rest _dotfiles_path _dotfiles_dir _dotfiles_real
fi

export EDITOR='nano'
export DOCKER_BUILDKIT=1

export GITHUB_API_URL=https://api.github.com
export GITHUB_GRAPHQL_URL=https://api.github.com/graphql

# ~/.env and ~/.env.host are generated from Bitwarden (`machine env pull`).
# Local overrides, including BW_SESSION: ~/.env.local (never overwritten).
# load customization
# Expand ${NAME} like docker compose does, without executing the value.
_envfile_expand() {
    local rest=$1 out='' name
    # shellcheck disable=SC2016 # Literal ${...} patterns are parsed, not expanded.
    while [[ $rest == *'${'*'}'* ]]; do
        out+=${rest%%'${'*}
        rest=${rest#*'${'}
        name=${rest%%'}'*}
        rest=${rest#*'}'}
        if [[ $name =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            out+=$(printenv "$name")
        else
            out+='${'$name'}'
        fi
    done
    printf '%s' "$out$rest"
}
# enable nullglob in a shell-agnostic way
if [[ -n ${ZSH_VERSION:-} ]]; then
    setopt nullglob
else
    shopt -s nullglob
fi
for envfile in ~/.env ~/.env.host ~/.env.local; do
    [[ -f $envfile ]] || continue
    # Check permissions: warn if world-readable or writable
    perms=$(stat -c %a "$envfile")
    if [[ $perms -gt 600 ]]; then
        echo "WARNING: $envfile permissions ($perms) are too open. Should be 600 use 'chmod 600 $envfile'."
    fi
    # Detect if envfile uses 'export' (ignoring comments and blank lines)
    if grep -E '^[[:space:]]*export[[:space:]]+' "$envfile" | grep -vq '^#'; then
        set -a
        source "$envfile"
        set +a
    else
        # shellcheck disable=SC2163
        while IFS= read -r line; do
            # Skip comments and blank lines
            [[ $line =~ ^[[:space:]]*# ]] && continue
            [[ -z $line ]] && continue
            # Export variable
            if [[ $line =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]]; then
                key=${line%%=*}
                export "${key//[[:space:]]/}=$(_envfile_expand "${line#*=}")"
            fi
        done <"$envfile"
    fi
done
unset key
unset -f _envfile_expand
if [[ -n ${ZSH_VERSION:-} ]]; then
    unsetopt nullglob
else
    shopt -u nullglob
fi
