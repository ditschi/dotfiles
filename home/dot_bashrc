# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples
# shellcheck shell=bash

# If not running interactively, don't do anything
case $- in
    *i*) ;;
    *) return ;;
esac

# Auto-switch to zsh if available (workaround when chsh doesn't work)
# Do NOT auto-switch if bash was started manually (from another shell or nested bash)
if [ -z "$ZSH_VERSION" ]; then
    parent_shell=$(ps -p "$PPID" -o comm=)
    shlvl_gt_1="no"
    if [ "$SHLVL" -gt 1 ]; then
        shlvl_gt_1="yes"
    fi
    case "$parent_shell:$shlvl_gt_1" in
        zsh:*|bash:*|fish:*|dash:*|ksh:*|tcsh:*|csh:*)
            # Bash was started manually from another shell, skip auto-switch
            ;;
        *:yes)
            # Nested bash shell, skip auto-switch
            ;;
        *)
            # Always honor preferred shell if set and not bash
            if [ -f "$HOME/.preferred-shell" ]; then
                preferred_shell=$(cat "$HOME/.preferred-shell" | tr -d '[:space:]')
                if [ "$preferred_shell" != "bash" ] && [ "$preferred_shell" != "/bin/bash" ] && command -v "$preferred_shell" >/dev/null 2>&1; then
                    handoff_ok=yes
                    if [ "${preferred_shell##*/}" = "zsh" ] && [ -r "$HOME/.zsh/zsh-handoff-check.sh" ]; then
                        . "$HOME/.zsh/zsh-handoff-check.sh"
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
                if command -v zsh >/dev/null 2>&1; then
                    if [ -z "$BASH_EXECUTION_STRING" ]; then
                        handoff_ok=yes
                        if [ -r "$HOME/.zsh/zsh-handoff-check.sh" ]; then
                            . "$HOME/.zsh/zsh-handoff-check.sh"
                            dotfiles_zsh_handoff_ok || handoff_ok=no
                        fi
                        if [ "$handoff_ok" = yes ]; then
                            SHELL=$(command -v zsh)
                            export SHELL
                            exec zsh -l
                        fi
                    fi
                fi
            fi
            unset handoff_ok preferred_shell
            ;;
    esac
fi

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

[ -f /usr/share/bash-completion/completions/git ] && source /usr/share/bash-completion/completions/git

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

# Tools of the mise fragments (fzf, zoxide, starship, ...); a host without mise skips this.
if [ -d "$HOME/.local/bin" ]; then
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) ;;
        *) PATH="$HOME/.local/bin:$PATH" ;;
    esac
fi
if command -v mise >/dev/null 2>&1; then
    eval "$(mise activate bash)"
fi

DOTFILES_DIR="${HOME}/.zsh/config"
if [ -d "$DOTFILES_DIR" ]; then
    . "$DOTFILES_DIR/00_alias.zsh"
    . "$DOTFILES_DIR/01_env.zsh"
    . "$DOTFILES_DIR/05_pyenv.zsh"
    . "$DOTFILES_DIR/06_history.zsh"

    # MACHINE_PROFILE / WORK_SETUP, shared with zsh
    . "$HOME/.zsh/machine-profile.sh"
    # work modules are only linked on work-machine, not in dev containers
    if [ "${WORK_SETUP:-}" = "true" ] && [ -f "$DOTFILES_DIR/01_work.zsh" ]; then
        . "$DOTFILES_DIR/01_work_tools.zsh"
        . "$DOTFILES_DIR/01_work.zsh"
    fi
fi

# Update state: segment in the prompt (Starship env_var module, or a PS1 prefix), one line at start
# only for needs-attention.
if [ -r "$HOME/.zsh/update-state.sh" ]; then
    # shellcheck source=/dev/null
    . "$HOME/.zsh/update-state.sh"
    dotfiles_update_startup
fi

# Tab completion for machine (Python CLI)
if command -v machine >/dev/null 2>&1; then
    eval "$(machine completion bash 2>/dev/null)"
fi

# Shared with zsh: the plugin checkouts of antidote (cloned by the first zsh start) and the
# cached tool init (dotfiles_cache_eval). bash has no plugin manager of its own.
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
    _dotfiles_dir="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/lscolors.bash"
    if [ ! -s "$_dotfiles_dir" ] || [ "$_dotfiles_plugins/trapd00r/LS_COLORS/LS_COLORS" -nt "$_dotfiles_dir" ]; then
        mkdir -p "${_dotfiles_dir%/*}" && dircolors -b "$_dotfiles_plugins/trapd00r/LS_COLORS/LS_COLORS" >"$_dotfiles_dir"
    fi
    # shellcheck source=/dev/null
    . "$_dotfiles_dir"
fi
unset _dotfiles_plugins _dotfiles_dir
LS_COLORS=$LS_COLORS:'di=0;32'
export LS_COLORS

[ -r "$HOME/.zsh/cache-eval.sh" ] && . "$HOME/.zsh/cache-eval.sh"
if declare -F dotfiles_cache_eval >/dev/null; then
    dotfiles_cache_eval fzf fzf --bash
    dotfiles_cache_eval zoxide zoxide init bash
fi

# Up/Down search the history for the typed prefix; Esc Esc puts sudo in front of the line.
bind '"\e[A": history-search-backward' '"\e[B": history-search-forward'
bind '"\eOA": history-search-backward' '"\eOB": history-search-forward'
_dotfiles_sudo_command_line() {
    if [ -z "$READLINE_LINE" ]; then
        READLINE_LINE=$(fc -ln -1 2>/dev/null)
        READLINE_LINE=${READLINE_LINE#"${READLINE_LINE%%[![:space:]]*}"}
    fi
    if [ "${READLINE_LINE#sudo }" != "$READLINE_LINE" ]; then
        READLINE_LINE=${READLINE_LINE#sudo }
    else
        READLINE_LINE="sudo $READLINE_LINE"
    fi
    READLINE_POINT=${#READLINE_LINE}
}
bind -x '"\e\e": _dotfiles_sudo_command_line'

# Pasted commands: strip a leading `❯ ` or `$ ` prompt indicator. `$` cannot be a bash
# function or alias, so the not-found handler runs it (in a subshell: `$ cd dir` does not
# change the directory). Other unknown commands go to the previous handler, if any.
eval '❯() { "$@"; }'
if declare -F command_not_found_handle >/dev/null; then
    eval "_dotfiles_command_not_found_handle()$(declare -f command_not_found_handle | tail -n +2)"
fi
command_not_found_handle() {
    if [ "$1" = '$' ]; then
        shift
        "$@"
        return
    fi
    if declare -F _dotfiles_command_not_found_handle >/dev/null; then
        _dotfiles_command_not_found_handle "$@"
        return
    fi
    printf 'bash: %s: command not found\n' "$1" >&2
    return 127
}

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Prompt: Starship (~/.config/starship.toml, shared with zsh) when installed, else a plain PS1.
# Starship keeps this PROMPT_COMMAND and runs it before it draws the prompt.
PROMPT_COMMAND='history -a;history -r'
# keep the hook that `mise activate bash` added above (it updates tools after `mise use`)
declare -F _mise_hook_prompt_command >/dev/null && PROMPT_COMMAND="_mise_hook_prompt_command;$PROMPT_COMMAND"
declare -F dotfiles_update_prompt >/dev/null && PROMPT_COMMAND="$PROMPT_COMMAND;dotfiles_update_prompt"
declare -F dotfiles_cache_eval >/dev/null && dotfiles_cache_eval starship starship init bash --print-full-init
if ! declare -F starship_precmd >/dev/null; then
    PS1='${DOTFILES_UPDATE_SEGMENT:+$DOTFILES_UPDATE_SEGMENT }${debian_chroot:+($debian_chroot)}\[\033[01;34m\]\w\[\033[00m\] \[\033[01;35m\]❯\[\033[00m\] '
    case "$TERM" in
        xterm* | rxvt*) PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1" ;;
    esac
fi

# Local bashrc extension point (host-only additions, e.g. externally managed blocks)
# shellcheck source=/dev/null
[[ ! -f ~/.bashrc-local ]] || source ~/.bashrc-local
