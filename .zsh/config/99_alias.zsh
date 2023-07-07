alias zshalias="nano $ZSH/config/99_alias.zsh"

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

alias g='git'

alias ipv6-disable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1'
alias ipv6-enable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=0'
