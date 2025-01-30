alias zshplugins="nano $0"

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#ff00ff,bg=cyan,bold,underline"
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=8,bg=0,bold,underline'
ZSH_AUTOSUGGEST_STRATEGY=(history completion)

# Install the bin-gem-node annex
zinit light zdharma-continuum/zinit-annex-bin-gem-node

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
zinit pack"bgn" for fzf
zinit light Aloxaf/fzf-tab

# disable sort when completing `git checkout`
zstyle ':completion:*:git-checkout:*' sort false
# set descriptions format to enable group support
zstyle ':completion:*:descriptions' format '[%d]'
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
# preview directory's content with eza when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
# switch group using `,` and `.`
zstyle ':fzf-tab:*' switch-group ',' '.'
zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup

zinit light zsh-users/zsh-history-substring-search
zinit ice wait atload'_history_substring_search_config'

zinit ice wait'!0' zinit light skywind3000/z.lua
