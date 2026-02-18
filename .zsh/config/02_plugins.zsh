alias zshplugins="nano $0"

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#ff00ff,bg=cyan,bold,underline"
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=8,bg=0,bold,underline'
ZSH_AUTOSUGGEST_STRATEGY=(history completion)

# Combined installation of multiple plugins:
# - hcgraf/zsh-sudo
# - zpm-zsh/undollar
# - agkozak/zsh-z
# - paulirish/git-open
# - fast-syntax-highlighting
# - zsh-autosuggestions
# - zsh-completions
zinit wait light-mode lucid for \
  hcgraf/zsh-sudo \
  zpm-zsh/undollar \
  agkozak/zsh-z \
  paulirish/git-open \
  atinit"zicompinit; zicdreplay" \
    @zdharma-continuum/fast-syntax-highlighting \
  atload"_zsh_autosuggest_start" \
  atinit"bindkey '^_' autosuggest-execute;bindkey '^ ' autosuggest-accept;" \
    @zsh-users/zsh-autosuggestions \
  blockf atpull'zinit creinstall -q .' \
    @zsh-users/zsh-completions

zinit as"program" for \
  paulirish/git-recent \
  eza-community/eza

zinit as"command" pick"git-recall" for Fakerr/git-recall

zinit ice as"command" from"gh-r" mv"fd* -> fd" pick"fd/fd"
zinit light sharkdp/fd

# https://github.com/zdharma-continuum/zsh-diff-so-fancy
zplugin ice as"program" pick"bin/git-dsf"
zplugin light zdharma-continuum/zsh-diff-so-fancy

# Install fzf with completions and additional scripts
zinit pack for fzf
zinit light Aloxaf/fzf-tab

# disable sort when completing `git checkout`
zstyle ':completion:*:git-checkout:*' sort false
# set descriptions format to enable group support
zstyle ':completion:*:descriptions' format '[%d]'
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
# Preview directory content when completing cd.
# Prefer eza, fallback to ls if eza isn't available.
if command -v eza >/dev/null 2>&1; then
  zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
else
  zstyle ':fzf-tab:complete:cd:*' fzf-preview 'ls -1 --color=always $realpath'
fi
# switch group using `,` and `.`
zstyle ':fzf-tab:*' switch-group ',' '.'
zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup

zinit ice wait lucid atload'(( $+functions[_history_substring_search_config] )) && _history_substring_search_config'
zinit light zsh-users/zsh-history-substring-search

if command -v lua >/dev/null 2>&1 || command -v luajit >/dev/null 2>&1; then
  zinit ice wait'!0' lucid
  zinit light skywind3000/z.lua
fi
