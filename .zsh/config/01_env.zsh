alias zshenv="nano $0"

export PATH="$PATH:$HOME/.local/bin"

export EDITOR='nano'
export DOCKER_BUILDKIT=1

# load customisation
[[ ! -f ~/.env ]] || source ~/.env
