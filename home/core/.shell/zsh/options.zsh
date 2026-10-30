export PATH="$HOME/bin:/usr/local/bin:$PATH"
export PATH="$PATH:$HOME/.local/bin"
alias zshconfig="nano ~/.zshrc"
alias zshenv="nano $HOME/.zshenv"

bindkey -e
setopt correct
fpath+=~/.zfunc
