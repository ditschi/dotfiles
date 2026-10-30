alias zshheys="nano $HOME/.shell/zsh/keybindings.zsh"

# The autosuggestion keys (Ctrl+Space accept, Ctrl+_ execute) are bound when
# zsh-autosuggestions has loaded (dotfiles_after_autosuggest in 02_plugins.zsh).

# Bind the delete key to delete the character under the cursor
bindkey "^[[3~" delete-char
# Bind the Home/End key to move the cursor to the beginning/end of the line
bindkey "^[[H" beginning-of-line
bindkey "^[[F" end-of-line

# Bind Up/Down to prefix history search.
# Some terminals send ^[[A/^[[B, others ^[OA/^[OB (application cursor mode).
# This function is intentionally called twice:
# - once now (fallback binding while the plugin is not loaded yet),
# - again from the plugins.txt post: hook once history-substring-search is available.
function _history_substring_search_config() {
    if (( $+widgets[history-substring-search-up] && $+widgets[history-substring-search-down] )); then
        for keymap in emacs viins vicmd; do
            bindkey -M "$keymap" '^[[A' history-substring-search-up
            bindkey -M "$keymap" '^[[B' history-substring-search-down
            bindkey -M "$keymap" '^[OA' history-substring-search-up
            bindkey -M "$keymap" '^[OB' history-substring-search-down
        done
    else
        autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
        zle -N up-line-or-beginning-search
        zle -N down-line-or-beginning-search
        for keymap in emacs viins vicmd; do
            bindkey -M "$keymap" '^[[A' up-line-or-beginning-search
            bindkey -M "$keymap" '^[[B' down-line-or-beginning-search
            bindkey -M "$keymap" '^[OA' up-line-or-beginning-search
            bindkey -M "$keymap" '^[OB' down-line-or-beginning-search
        done
    fi
}

_history_substring_search_config

# Bind the Right/Left arrow key to move the cursor forward one character
bindkey "^[[C" forward-char
bindkey "^[[D" backward-char

# Pasted commands: strip a leading `$ ` or `❯ ` prompt indicator.
alias \$=''
'❯'() { "$@" }

if [[ -o interactive && -r "$HOME/.shell/common/command-prefix.sh" ]]; then
  source "$HOME/.shell/common/command-prefix.sh"
  autoload -Uz add-zsh-hook add-zle-hook-widget

  _dotfiles_prefix_preexec() {
    _dotfiles_prefix_line=$1
    _dotfiles_prefix_pending=''
  }
  _dotfiles_prefix_precmd() {
    local command_status=$?
    _dotfiles_prefix_pending=''
    if ((command_status)) && dotfiles_command_prefix "${_dotfiles_prefix_line:-}"; then
      _dotfiles_prefix_pending=$DOTFILES_COMMAND_PREFIX_SUGGESTION
    fi
    _dotfiles_prefix_line=''
    return 0
  }
  _dotfiles_prefix_line_init() {
    if [[ -z $BUFFER ]] && (( ! PENDING && ! KEYS_QUEUED_COUNT )); then
      BUFFER=${_dotfiles_prefix_pending:-}
      CURSOR=${#BUFFER}
    fi
    _dotfiles_prefix_pending=''
  }
  add-zsh-hook preexec _dotfiles_prefix_preexec
  precmd_functions=(_dotfiles_prefix_precmd ${precmd_functions:#_dotfiles_prefix_precmd})
  add-zle-hook-widget line-init _dotfiles_prefix_line_init
fi

# Esc Esc toggles `sudo ` in front of the command line (the last command when the line is empty).
dotfiles_sudo_command_line() {
  [[ -z $BUFFER ]] && zle up-history
  if [[ $BUFFER == sudo\ * ]]; then
    BUFFER=${BUFFER#sudo }
    (( CURSOR = CURSOR > 5 ? CURSOR - 5 : 0 ))
  else
    BUFFER="sudo $BUFFER"
    (( CURSOR += 5 ))
  fi
}
zle -N dotfiles_sudo_command_line
bindkey -M emacs '\e\e' dotfiles_sudo_command_line
