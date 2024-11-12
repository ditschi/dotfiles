alias zshalias="nano $ZSH/config/00_alias.zsh"

alias update-dotfiles="cd ~/dotfiles/ && git pull && cd -"

alias python='python3'
alias docker-compose='docker compose'
alias dc='docker compose'

alias ls='ls --color=auto'
alias ll='ls -l --color=auto'
alias la='ls -a --color=auto'
alias lla='ls -la --color=auto'

alias xll='ls -alF'
alias xla='ls -A'
alias xl='ls -CF'

alias branch='git branch --no-color --show-current'
alias issue='git rev-parse --abbrev-ref HEAD | grep -Eo "[A-Z]+-[0-9]+"'
alias g='git'

alias ipv6-disable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1'
alias ipv6-enable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=0'


store-password() {
    if [ -n "$1" ]; then
        user="$1"
    else
        user="$(whoami)"
    fi

    secret-tool store --label "User Credentials" password "$user"
}

get-password() {
    if [ -n "$1" ]; then
        user="$1"
    else
        user="$(whoami)"
    fi

    secret-tool lookup password "$user"
}

clone_org_repos() {
  local OWNER=$1
  for repo in $(gh repo list $OWNER --limit 1000 --json name --jq '.[].name'); do
    gh repo clone $OWNER/$repo
  done
}
