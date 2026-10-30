# shellcheck shell=bash
alias zshwork-tools='nano "$HOME/.shell/work/common/tools.sh"'
# Work-only helpers. gh/az installation is handled by Ansible
# (features: gh-cli, work-cli) — see ansible/roles/gh_cli, ansible/roles/az_cli.

# shellcheck shell=bash
alias zshwork-tools='nano "$HOME/.shell/work/common/tools.sh"'
# Work-only helpers. gh/az installation is handled by Ansible
# (features: gh-cli, work-cli) — see ansible/roles/gh_cli, ansible/roles/az_cli.

if [[ ${WORK_SETUP} != "true" ]]; then # set by the shell startup loader
    return
fi

work-gh-login() {
    gh auth login -h github.boschdevcloud.com
}
