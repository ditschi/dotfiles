# Baseline: shared options, compinit and the Starship prompt, no plugins.
source ~/.zsh/common.zsh
spike_cache_eval starship starship init zsh --print-full-init
spike_compinit
spike_loaded
