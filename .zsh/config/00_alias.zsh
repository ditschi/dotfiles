alias zshalias="nano $0"

alias update-dotfiles="cd ~/dotfiles/ && git pull && cd -"

alias python='python3'
alias docker-compose='docker compose'
alias dc='docker compose'

# enable color support of ls and other tools
alias ls='ls --color=auto'
alias ll='ls -alF --color=auto'
alias la='ls -a --color=auto'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'


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
