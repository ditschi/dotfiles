alias zshplugins="nano $0"

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#ff00ff,bg=cyan,bold,underline"
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=8,bg=0,bold,underline'
ZSH_AUTOSUGGEST_STRATEGY=(history completion)

zinit light hcgraf/zsh-sudo
zinit light zdharma/fast-syntax-highlighting
zinit light zpm-zsh/undollar
zinit light agkozak/zsh-z
zinit light paulirish/git-open

zinit as"program" for paulirish/git-recent
zinit as"program" from"gh-r" for eza-community/eza

zinit as"command" pick"git-recall" for Fakerr/git-recall

zinit ice as"command" from"gh-r" mv"fd* -> fd" pick"fd/fd"
zinit light sharkdp/fd

# https://github.com/zdharma-continuum/zsh-diff-so-fancy
# zplugin ice as"program" pick"bin/git-dsf"
# zplugin light zdharma-continuum/zsh-diff-so-fancy

# marlonrichert/zsh-autocomplete \
# as"program" pick"bin/git-fuzzy" \
#   bigH/git-fuzzy \
# ytakahashi/igit \


# todo autojump https://github.com/wting/autojump

zinit as"program" from"gh-r" for junegunn/fzf-bin
zinit light Aloxaf/fzf-tab
# disable sort when completing `git checkout`
zstyle ':completion:*:git-checkout:*' sort false
# set descriptions format to enable group support
zstyle ':completion:*:descriptions' format '[%d]'
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s:.:.)LS_COLORS}
# preview directory's content with eza when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
# switch group using `,` and `.`
zstyle ':fzf-tab:*' switch-group ',' '.'
zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup


zinit light zsh-users/zsh-autosuggestions
zinit light zsh-users/zsh-completions

zinit light zsh-users/zsh-history-substring-search
zinit ice wait atload'_history_substring_search_config'
