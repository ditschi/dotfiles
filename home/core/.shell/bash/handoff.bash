# Bash-to-zsh handoff. Sourced only after the interactive Bash guard.
# Auto-switch to zsh if available (workaround when chsh doesn't work).
# Do NOT auto-switch if bash was started manually (from another shell or nested bash).
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
            if [ -f "$HOME/.preferred-shell" ]; then
                preferred_shell=$(cat "$HOME/.preferred-shell" | tr -d '[:space:]')
                if [ "$preferred_shell" != "bash" ] && [ "$preferred_shell" != "/bin/bash" ] && command -v "$preferred_shell" >/dev/null 2>&1; then
                    handoff_ok=yes
                    if [ "${preferred_shell##*/}" = "zsh" ] && [ -r "$HOME/.shell/bash/zsh-health.bash" ]; then
                        . "$HOME/.shell/bash/zsh-health.bash"
                        dotfiles_zsh_handoff_ok || handoff_ok=no
                    fi
                    if [ "$handoff_ok" = yes ]; then
                        SHELL=$(command -v "$preferred_shell")
                        export SHELL
                        exec "$preferred_shell" -l
                    fi
                fi
            fi
            if [ ! -f /.dockerenv ] && [ "${handoff_ok:-yes}" = yes ]; then
                if command -v zsh >/dev/null 2>&1 && [ -z "$BASH_EXECUTION_STRING" ]; then
                    handoff_ok=yes
                    if [ -r "$HOME/.shell/bash/zsh-health.bash" ]; then
                        . "$HOME/.shell/bash/zsh-health.bash"
                        dotfiles_zsh_handoff_ok || handoff_ok=no
                    fi
                    if [ "$handoff_ok" = yes ]; then
                        SHELL=$(command -v zsh)
                        export SHELL
                        exec zsh -l
                    fi
                fi
            fi
            unset handoff_ok preferred_shell
            ;;
    esac
fi
