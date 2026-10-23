# Measurement only (not part of a candidate): first-prompt and fully-loaded markers.
# Last step of every config: everything is loaded (cf. DOTFILES_ZSH_LOADED).
# SPIKE_T0 (EPOCHREALTIME at launch) + SPIKE_REPORT: write loaded_ms and a feature check.
zmodload zsh/datetime
spike_features() {
  local -A f=(
    compsys        $+functions[compdef]
    fzf_tab        $+functions[fzf-tab-complete]
    autosuggest    $+functions[_zsh_autosuggest_start]
    highlight      $(( $+functions[_zsh_highlight] || $+functions[_zsh_highlight_widget_orig-s0.0000-redisplay] || $+functions[-fast-highlight-process] || $+functions[_zsh_highlight_highlighter_main_paint] ))
    hss            $+functions[history-substring-search-up]
    sudo           $(( $+widgets[sudo-command-line] || $+functions[sudo-command-line] ))
    undollar       $+aliases[\$]
    fzf_history    $+widgets[fzf-history-widget]
    zoxide         $+functions[__zoxide_z]
    ls_colors      $(( ${#LS_COLORS} > 1000 ))
    correct        ${options[correct]/on/1}
    key_accept     $([[ $(bindkey '^ ') == *autosuggest-accept ]] && print 1 || print 0)
    key_execute    $([[ $(bindkey '^_') == *autosuggest-execute ]] && print 1 || print 0)
    key_up_hss     $([[ $(bindkey '^[[A') == *history-substring-search-up ]] && print 1 || print 0)
    key_sudo       $([[ $(bindkey '\e\e') == *sudo-command-line ]] && print 1 || print 0)
    key_ctrl_r     $([[ $(bindkey '^R') == *fzf-history-widget ]] && print 1 || print 0)
    key_tab        $([[ $(bindkey '^I') == *fzf-tab-complete ]] && print 1 || print 0)
  )
  local k out=()
  for k in ${(ko)f}; do out+=("$k=${f[$k]/off/0}"); done
  print -r -- ${(j: :)out}
}
# line-init: the prompt is drawn and the editor accepts input.
# With SPIKE_EXIT_WHEN_LOADED the shell exits once it is both prompted and loaded.
spike_report() {
  [[ -n $SPIKE_T0 && -n $SPIKE_REPORT ]] &&
    print -r -- "$1=$(( (EPOCHREALTIME - SPIKE_T0) * 1000 ))${2:+ $2}" >>| $SPIKE_REPORT
  return 0
}
spike_maybe_exit() {
  (( ${+SPIKE_EXIT_WHEN_LOADED} && ${+SPIKE_PROMPTED} && ${+SPIKE_LOADED} )) && kill -HUP $$
  return 0
}
spike_first_prompt() {
  typeset -g SPIKE_PROMPTED=1
  spike_report prompt_ms
  add-zle-hook-widget -d line-init spike_first_prompt
  spike_maybe_exit
}
autoload -Uz add-zle-hook-widget
add-zle-hook-widget line-init spike_first_prompt
spike_loaded() {
  typeset -g SPIKE_LOADED=1
  spike_report loaded_ms "$(spike_features)"
  spike_maybe_exit
}
