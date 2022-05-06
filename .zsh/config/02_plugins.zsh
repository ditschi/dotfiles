
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=5'
ZSH_AUTOSUGGEST_STRATEGY=(history completion)

. /usr/share/autojump/autojump.sh

# zinit pack"binary" for fzf

zinit wait lucid light-mode for \
  atinit'zicompinit' \
    Aloxaf/fzf-tab \
  atinit'zicompinit; zicdreplay' \
    zdharma-continuum/fast-syntax-highlighting \
  atload'_zsh_autosuggest_start; bindkey "$key[Up]" history-beginning-search-backward; bindkey "$key[Down]" history-beginning-search-forward' \
    zsh-users/zsh-autosuggestions \
  blockf atpull'zinit creinstall -q .' \
    zsh-users/zsh-completions \
  hcgraf/zsh-sudo \
  arzzen/calc.plugin.zsh \
  zpm-zsh/undollar


# marlonrichert/zsh-autocomplete \
# as"program" pick"bin/git-fuzzy" \
#   bigH/git-fuzzy \
# ytakahashi/igit \


# todo autojump https://github.com/wting/autojump
