# Bash fallback (spike): Starship, fzf, zoxide, LS_COLORS; plain readline, no ble.sh.
[[ $- == *i* ]] || return
source ~/.bash/common.bash
# readline: Up/Down prefix search (no substring search), Esc Esc prepends sudo
bind '"\e[A": history-search-backward' '"\e[B": history-search-forward'
bind '"\e\e": "\C-asudo \C-e"'
PROMPT_COMMAND+=(spike_bash_prompt)
