# Near-equal bash (spike): ble.sh (suggestions, highlighting, substring search, menus) + the fallback.
[[ $- == *i* ]] || return
source /opt/blesh/ble.sh --noattach
source ~/.bash/common.bash
if [[ ${BLE_VERSION-} ]]; then
  ble-import -d integration/fzf-key-bindings   # Ctrl+R / Ctrl+T through ble.sh
  ble-bind -m emacs -f up 'history-substring-search-backward'
  ble-bind -m emacs -f down 'history-substring-search-forward'
  ble-bind -m emacs -f C-SP 'auto_complete/insert'            # accept suggestion
  ble-bind -m auto_complete -f C-SP 'auto_complete/insert'
  ble-bind -m emacs -f 'C-_' 'auto_complete/insert-and-accept-line' 2>/dev/null
  ble-bind -m emacs -c 'ESC ESC' 'READLINE_LINE="sudo $READLINE_LINE"; READLINE_POINT=${#READLINE_LINE}'
fi
PROMPT_COMMAND+=(spike_bash_prompt)
[[ ${BLE_VERSION-} ]] && ble-attach
