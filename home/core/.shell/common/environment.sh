# shellcheck shell=bash
export PATH="$PATH:$HOME/.local/bin"

# VS Code's copilotCLIShim drops its dir from PATH by literal match on its realpath;
# a symlinked $HOME would otherwise make it start itself recursively.
# The helpers are removed again at the end of the file.
_dotfiles_resolve_copilot_dir() {
    [[ $_dotfiles_dir == /*/github.copilot-chat/copilotCli && -d $_dotfiles_dir ]] || return 0
    # shellcheck disable=SC2034 # Keeps zsh chpwd hooks (zoxide) quiet in the subshell.
    _dotfiles_real=$(chpwd_functions=() && cd -P -- "$_dotfiles_dir" && pwd -P) &&
        _dotfiles_dir=$_dotfiles_real
    return 0
}

_dotfiles_resolve_copilot_path() {
    _dotfiles_rest=$PATH: _dotfiles_path=
    while [[ -n $_dotfiles_rest ]]; do
        _dotfiles_dir=${_dotfiles_rest%%:*}
        _dotfiles_rest=${_dotfiles_rest#*:}
        _dotfiles_resolve_copilot_dir
        _dotfiles_path+=:$_dotfiles_dir
    done
    export PATH=${_dotfiles_path#:}
    unset _dotfiles_rest _dotfiles_path _dotfiles_dir _dotfiles_real
}

# SSH agent: keep SSH_AUTH_SOCK (forwarding, desktop session), else use the socket of
# the systemd user unit ssh-agent.socket; never start an agent (spec ssh-agent).
_dotfiles_use_agent_socket() {
    [ -z "${SSH_AUTH_SOCK:-}" ] && [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -S "$XDG_RUNTIME_DIR/openssh_agent" ]
}

if [[ $PATH == */github.copilot-chat/copilotCli* ]]; then
    _dotfiles_resolve_copilot_path
fi

if _dotfiles_use_agent_socket; then
    export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/openssh_agent"
fi
unset -f _dotfiles_resolve_copilot_dir _dotfiles_resolve_copilot_path _dotfiles_use_agent_socket

export EDITOR='nano'
export DOCKER_BUILDKIT=1

export GITHUB_API_URL=https://api.github.com
export GITHUB_GRAPHQL_URL=https://api.github.com/graphql

# ~/.env and ~/.env.host are generated from Bitwarden (`machine env pull`).
# Local overrides, including BW_SESSION: ~/.env.local (never overwritten).
_dotfiles_common=${BASH_SOURCE[0]:-$0}
_dotfiles_common=${_dotfiles_common%/*}
# During an update the checkout may hold envfiles.sh before it is linked into $HOME.
[[ -r $_dotfiles_common/envfiles.sh ]] ||
    _dotfiles_common=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]:-$0}")")
# shellcheck source=envfiles.sh
. "$_dotfiles_common/envfiles.sh"
dotfiles_load_envfiles
unset _dotfiles_common
unset -f _envfile_expand _envfile_fix_perms _envfile_parse dotfiles_load_envfiles
