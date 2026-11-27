# Bash-to-zsh handoff. Sourced only after the interactive Bash guard.
# Auto-switch to zsh if available (workaround when chsh doesn't work).
# Do NOT auto-switch if bash was started manually (from another shell or nested bash).
# The helpers are removed again at the end, so the interactive shell does not keep them.

# True if $1 names a shell other than bash that is installed.
_dotfiles_handoff_other_shell() {
    [ "$1" != "bash" ] && [ "$1" != "/bin/bash" ] && command -v "$1" >/dev/null 2>&1
}

# Sets handoff_ok; for zsh ($1) only when the zsh health check passes.
_dotfiles_handoff_check() {
    handoff_ok=yes
    [ "${1##*/}" = "zsh" ] || return 0
    [ -r "$HOME/.shell/bash/zsh-health.bash" ] || return 0
    . "$HOME/.shell/bash/zsh-health.bash"
    dotfiles_zsh_handoff_ok || handoff_ok=no
}

# Replaces bash with login shell $1 when handoff_ok allows it.
_dotfiles_handoff_exec() {
    [ "$handoff_ok" = yes ] || return 0
    SHELL=$(command -v "$1")
    export SHELL
    exec "$1" -l
}

# The shell named in ~/.preferred-shell, unless it is bash.
_dotfiles_handoff_preferred() {
    [ -f "$HOME/.preferred-shell" ] || return 0
    preferred_shell=$(cat "$HOME/.preferred-shell" | tr -d '[:space:]')
    _dotfiles_handoff_other_shell "$preferred_shell" || return 0
    _dotfiles_handoff_check "$preferred_shell"
    _dotfiles_handoff_exec "$preferred_shell"
}

# zsh, outside Docker, unless the preferred shell's check failed or bash runs a command string.
_dotfiles_handoff_zsh() {
    [ ! -f /.dockerenv ] && [ "${handoff_ok:-yes}" = yes ] || return 0
    command -v zsh >/dev/null 2>&1 && [ -z "$BASH_EXECUTION_STRING" ] || return 0
    _dotfiles_handoff_check zsh
    _dotfiles_handoff_exec zsh
}

if [ -z "$ZSH_VERSION" ]; then
    parent_shell=$(ps -p "$PPID" -o comm=)
    shlvl_gt_1="no"
    if [ "$SHLVL" -gt 1 ]; then
        shlvl_gt_1="yes"
    fi
    case "$parent_shell:$shlvl_gt_1" in
        zsh:* | bash:* | fish:* | dash:* | ksh:* | tcsh:* | csh:*) ;;
        *:yes) ;;
        *)
            _dotfiles_handoff_preferred
            _dotfiles_handoff_zsh
            unset handoff_ok preferred_shell
            ;;
    esac
fi
unset -f _dotfiles_handoff_other_shell _dotfiles_handoff_check _dotfiles_handoff_exec \
    _dotfiles_handoff_preferred _dotfiles_handoff_zsh
