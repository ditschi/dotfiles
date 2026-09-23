# Tab completion for `machine` (Python CLI). Loaded after zinit/compinit.
# Regenerate with: machine completion zsh

if ! typeset -f compdef >/dev/null 2>&1; then
    return
fi

_machine() {
    local -a commands
    commands=(
        'setup:Bootstrap this host or push via --limit'
        'update:git pull, chezmoi apply, Bitwarden env'
        'env:pull or status for ~/.env from Bitwarden'
        'status:git / chezmoi / profile'
        'commit:commit tracked changes'
        'push:git push'
        'inventory:ansible-vault edit/encrypt'
        'completion:print shell completion script'
        'help:show help'
    )
    local -a env_cmds inventory_cmds shells
    env_cmds=(pull status)
    inventory_cmds=(edit encrypt decrypt view)
    shells=(bash zsh)

    _arguments -C \
        '1: :->command' \
        '*:: :->args'

    case $state in
        command)
            _describe -t commands 'command' commands
            ;;
        args)
            case $words[1] in
                setup)
                    _arguments \
                        '--profile[machine profile]:profile:(work-laptop home-laptop home-server rpi rpi-zero container)' \
                        '--features[features]:features:(zsh-full fonts starship desktop gnome cosmic docker kerberos monitoring)' \
                        '--yes[non-interactive]' \
                        '--local[force local connection]' \
                        '--limit[ansible host]:host:' \
                        '--playbook[playbook]:playbook:(workstation homelab site)' \
                        '--skip-ansible' \
                        '--skip-chezmoi' \
                        '--no-become'
                    ;;
                update)
                    _arguments '--system[run ansible workstation]' '--force[ignore dirty git]'
                    ;;
                env)
                    _describe -t env_cmds 'env command' env_cmds
                    ;;
                inventory)
                    if ((CURRENT == 2)); then
                        _describe -t inventory_cmds 'inventory action' inventory_cmds
                    else
                        _files
                    fi
                    ;;
                commit)
                    _arguments '-m[message]:message:'
                    ;;
                completion)
                    _describe -t shells 'shell' shells
                    ;;
            esac
            ;;
    esac
}

compdef _machine machine
