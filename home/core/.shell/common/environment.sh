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

# SSH agent: keep SSH_AUTH_SOCK (forwarding, desktop session), else use the socket of
# the systemd user unit ssh-agent.socket; never start an agent (spec ssh-agent).
if [ -z "${SSH_AUTH_SOCK:-}" ] && [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -S "$XDG_RUNTIME_DIR/openssh_agent" ]; then
    export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/openssh_agent"
fi

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
unset -f _envfile_expand dotfiles_load_envfiles
