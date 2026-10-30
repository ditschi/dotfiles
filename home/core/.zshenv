# Ubuntu's /etc/zsh/zshrc runs compinit unless this is set; the dotfiles run it once
# themselves (deferred, see ~/.shell/zsh/plugins.zsh).
skip_global_compinit=1

# Shims of the mise tools (Git, git-lfs, ...) for non-interactive callers: IDEs, hooks, ssh commands.
if [ -d "$HOME/.local/share/mise/shims" ]; then
    export PATH="$HOME/.local/share/mise/shims:$PATH"
fi
