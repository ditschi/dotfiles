# set PATH to include user's private bin if it exists
if [ -d "$HOME/bin" ]; then
    PATH="$HOME/bin:$PATH"
fi

# set PATH to include user's private bin if it exists
if [ -d "$HOME/.local/bin" ]; then
    PATH="$HOME/.local/bin:$PATH"
fi

if command -v pyenv >/dev/null 2>&1; then
    export PYENV_ROOT="$HOME/.pyenv"
    [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
fi

# ensure to start ssh-agent
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval "$(ssh-agent -s)"
fi
