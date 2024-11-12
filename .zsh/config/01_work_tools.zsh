alias zshwork-tools="nano $0"
# Check and install tools

if [[ "$WORK_SETUP" != "true" ]]; then # WORK_SETUP is set by LOADER
    return
fi

if ! command -v gh &>/dev/null; then
    echo "GitHub CLI not found, installing..."
    # install https://github.com/cli/cli/blob/trunk/docs/install_linux.md
    (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y))
    sudo mkdir -p -m 755 /etc/apt/keyrings
    wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
    sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
    sudo apt update
    sudo apt install gh -y

    gh auth login -h github.boschdevcloud.com
fi

if ! command -v az &>/dev/null; then
    echo "Azure CLI not found, installing..."
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
fi
