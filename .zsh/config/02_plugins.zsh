alias zshplugins="nano $ZSH/config/02_plugins.zsh"

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=5'
ZSH_AUTOSUGGEST_STRATEGY=(history completion)

. /usr/share/autojump/autojump.sh

# zinit pack"binary" for fzf

zinit wait lucid light-mode for \
  blockf atpull'zinit creinstall -q .' \
    zsh-users/zsh-completions \
  atinit'zicompinit' \
    Aloxaf/fzf-tab \
  atinit'zicompinit; zicdreplay' \
    zdharma-continuum/fast-syntax-highlighting \
  atload'_zsh_autosuggest_start; bindkey "$key[Up]" history-beginning-search-backward; bindkey "$key[Down]" history-beginning-search-forward' \
    zsh-users/zsh-autosuggestions \
  hcgraf/zsh-sudo \
  arzzen/calc.plugin.zsh \
  zpm-zsh/undollar

# disable sort when completing `git checkout`
zstyle ':completion:*:git-checkout:*' sort false
# set descriptions format to enable group support
zstyle ':completion:*:descriptions' format '[%d]'
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
# preview directory's content with exa when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'exa -1 --color=always $realpath'
# switch group using `,` and `.`
zstyle ':fzf-tab:*' switch-group ',' '.'


# marlonrichert/zsh-autocomplete \
# as"program" pick"bin/git-fuzzy" \
#   bigH/git-fuzzy \
# ytakahashi/igit \


# todo autojump https://github.com/wting/autojump
