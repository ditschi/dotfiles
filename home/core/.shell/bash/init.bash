# Ordered interactive Bash includes. The entry point handles the handoff first.
_dotfiles_shell="$HOME/.shell"
. "$_dotfiles_shell/common/machine-profile.sh"
. "$_dotfiles_shell/common/cache-eval.sh"
. "$_dotfiles_shell/common/update-state.sh"
. "$_dotfiles_shell/bash/options.bash"
. "$_dotfiles_shell/bash/tools.bash"
. "$_dotfiles_shell/common/environment.sh"
. "$_dotfiles_shell/common/aliases.sh"
. "$_dotfiles_shell/bash/history.bash"
if [ "${WORK_SETUP:-}" = "true" ] &&
    [ -f "$_dotfiles_shell/work/common/tools.sh" ] &&
    [ -f "$_dotfiles_shell/work/common/environment.sh" ]; then
    . "$_dotfiles_shell/work/common/tools.sh"
    . "$_dotfiles_shell/work/common/environment.sh"
fi
dotfiles_update_startup
. "$_dotfiles_shell/bash/readline.bash"
. "$_dotfiles_shell/bash/prompt.bash"
unset _dotfiles_shell
