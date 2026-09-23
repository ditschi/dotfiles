alias zshpyenv="nano $0"

if command -v pyenv >/dev/null 2>&1; then
    export PYENV_ROOT="$HOME/.pyenv"
    [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    # Load pyenv-virtualenv automatically
    eval "$(pyenv virtualenv-init -)"
fi
