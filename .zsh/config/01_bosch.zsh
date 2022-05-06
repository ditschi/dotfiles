if [[ ! $USER =~ (^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$) ]]; then
    echo "Not lodading Bosch config as user '$USER' is not matching pattern"

    # ensure the default user in .gitconfig
    git config --global user.name "Christian Ditscher"
    git config --global user.email "chris@ditscher.me"
    return
fi
echo "User '$USER' matches bosch username pattern -> lodading Bosch config"

### MODIFIED BY OSD-PROXY-PACKAGE BEGIN ###

# Kerberos token check in bash prompt
PROMPT_COMMAND=__prompt_command

__prompt_command() {
    if klist -s ; then
        export KRB_STATUS_MSG=""
    else
        export KRB_STATUS_MSG="(No Kerberos token, run kinit) "
    fi
}

RED="\[$(tput setaf 1)\]"
RESET="\[$(tput sgr0)\]"
PS1="${RED}\${KRB_STATUS_MSG}${RESET}${PS1}"

### MODIFIED BY OSD-PROXY-PACKAGE END ###


# set the Bosch user in .gitconfig
git config --global user.name "Ditscher Christian (XC-DX/EAS3)"
git config --global user.email "Christian.Ditscher@de.bosch.com"

# proxy setup
export http_proxy=http://localhost:3128
export https_proxy=http://localhost:3128
export ftp_proxy=:http://localhost:3128
export no_proxy=localhost,127.0.0.1,*.microsoftonline.com,*.bosch.com

# dev-env setup
export DOCKER_USER=$(whoami) && export DOCKER_UID=$(id -u) && export DOCKER_GID=$(id -g)
export CONTAINER_USER=$(whoami) && export CONTAINER_UID=$(id -u) && export CONTAINER_GID=$(id -g)
export ARTIFACTORY_API_KEY  # from ~/env file
export CONAN_LOGIN_USERNAME=dci2lr

# functions

alias ldapsearch-bosch="ldapsearch -D dc=bosch,dc=com -Z -h rb-gc-12.de.bosch.com:3268"

ldap-groups () {
  username=$1
  ldapsearch-bosch -cn "$username" memberOf
}


# aliases
alias zshbosch="nano $ZSH/config/01_bosch.zsh"
alias chsh-bosch="echo 'https://inside-docupedia.bosch.com/confluence/display/BSC2OSD/Change+default+shell+from+bash+to+zsh \n \
    1. sudo nano /etc/sssd/sssd.conf \n \
        default_shell = /bin/bash \n \
        override_shell = /bin/zsh # <- add this \n \
    2. sudo rm /var/lib/sss/db/cache_de.bosch.com.ldb /var/lib/sss/db/ccache_DE.BOSCH.COM && sudo systemctl restart sssd \n \
    3. restart session'"

alias sde='docker-compose build dev-env && docker-compose run --rm -v ${HOME}/.zshrc:${HOME}/.zshrc -v ${HOME}/.zsh/:${HOME}/.zsh/ -v ${HOME}/.zprofile:${HOME}/.zprofile -v ${HOME}/.zprofile:${HOME}/.zprofile dev-env'


alias ldap-userdetails="ldapsearch-bosch -cn=" # <USER-ID>
alias ldap-usergroups="ldap-groups" # <USER-ID>

## ansible
alias ap="ansible-playbook"
alias ave="ansible-vault encrypt"
alias avd="ansible-vault decrypt"
