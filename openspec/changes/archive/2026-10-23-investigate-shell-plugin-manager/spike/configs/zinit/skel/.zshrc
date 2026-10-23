# Candidate: zinit with turbo (wait), rebuilt from the feature list.
ZINIT_HOME=${XDG_DATA_HOME:-$HOME/.local/share}/zinit/zinit.git
[[ -d $ZINIT_HOME/.git ]] || git clone -q --depth 1 https://github.com/zdharma-continuum/zinit.git $ZINIT_HOME
source $ZINIT_HOME/zinit.zsh

source ~/.zsh/common.zsh
spike_cache_eval starship starship init zsh --print-full-init

# Turbo: loaded in this order after the first prompt.
zinit wait lucid light-mode depth=1 for \
  blockf atpull'zinit creinstall -q .' \
    zsh-users/zsh-completions \
  id-as'ls_colors' atload'spike_lscolors ${ZINIT[PLUGINS_DIR]}/ls_colors/LS_COLORS' \
    trapd00r/LS_COLORS \
  atinit'spike_compinit; zicdreplay -q; spike_tools' \
    Aloxaf/fzf-tab \
  hcgraf/zsh-sudo \
  zpm-zsh/undollar \
  atload'spike_after_hss' \
    zsh-users/zsh-history-substring-search \
  atload'_zsh_autosuggest_start; spike_after_autosuggest' \
    zsh-users/zsh-autosuggestions \
  atload'spike_loaded' \
    zdharma-continuum/fast-syntax-highlighting
