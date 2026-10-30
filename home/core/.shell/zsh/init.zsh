# Ensure ZSH variable is set
DOTFILES_SHELL=${DOTFILES_SHELL:-$HOME/.shell}
ZSH=${ZSH:-$DOTFILES_SHELL/zsh}

source "$DOTFILES_SHELL/common/machine-profile.sh"

source "$DOTFILES_SHELL/common/update-state.sh"

source "$DOTFILES_SHELL/common/cache-eval.sh"

source "$DOTFILES_SHELL/zsh/options.zsh"
source "$DOTFILES_SHELL/common/aliases.sh"
source "$DOTFILES_SHELL/zsh/tools.zsh"
source "$DOTFILES_SHELL/common/environment.sh"

if [[ $WORK_SETUP == true ]]; then
    [[ ! -r $DOTFILES_SHELL/work/common/tools.sh ]] || source "$DOTFILES_SHELL/work/common/tools.sh"
    [[ ! -r $DOTFILES_SHELL/work/common/environment.sh ]] || source "$DOTFILES_SHELL/work/common/environment.sh"
    [[ ! -r $DOTFILES_SHELL/work/zsh/ldap-helpers.zsh ]] || source "$DOTFILES_SHELL/work/zsh/ldap-helpers.zsh"
fi

source "$DOTFILES_SHELL/zsh/history.zsh"
source "$DOTFILES_SHELL/zsh/plugins.zsh"
source "$DOTFILES_SHELL/zsh/prompt.zsh"
source "$DOTFILES_SHELL/zsh/keybindings.zsh"

# Health check mode only (DOTFILES_ZSH_CHECK=1): run the queued deferred plugin steps now.
(( ! $+functions[dotfiles_run_deferred] )) || dotfiles_run_deferred

# Lets the Bash handoff check see that the config loaded completely.
typeset -g DOTFILES_ZSH_LOADED=1
