# shellcheck shell=bash
# Env file loader shared by environment.sh and get-password (spec env-files).

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

# Export the variables of ~/.env, ~/.env.host and ~/.env.local; later files win.
dotfiles_load_envfiles() {
    local envfile perms line key
    for envfile in "$HOME/.env" "$HOME/.env.host" "$HOME/.env.local"; do
        [[ -f $envfile ]] || continue
        # Group or other bits set: change to 600. Not during the zsh health check run,
        # whose stderr would fail the check and hide the message (spec env-files).
        perms=$(stat -c %a "$envfile")
        if [[ -z ${DOTFILES_ZSH_CHECK-} && ${perms: -2} != 00 ]]; then
            if chmod 600 "$envfile" 2>/dev/null; then
                echo "Fixed permissions of $envfile ($perms -> 600)." >&2
            else
                echo "WARNING: $envfile permissions ($perms) are too open. Should be 600 use 'chmod 600 $envfile'." >&2
            fi
        fi
        # Files with 'export' lines are sourced; plain KEY=value files are parsed.
        if grep -E '^[[:space:]]*export[[:space:]]+' "$envfile" | grep -vq '^#'; then
            set -a
            # shellcheck disable=SC1090
            source "$envfile"
            set +a
        else
            # shellcheck disable=SC2163
            while IFS= read -r line; do
                [[ $line =~ ^[[:space:]]*# ]] && continue
                [[ -z $line ]] && continue
                if [[ $line =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]]; then
                    key=${line%%=*}
                    export "${key//[[:space:]]/}=$(_envfile_expand "${line#*=}")"
                fi
            done <"$envfile"
        fi
    done
}
