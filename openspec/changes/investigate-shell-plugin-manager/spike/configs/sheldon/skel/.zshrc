# Candidate: sheldon + zsh-defer, rebuilt from the feature list.
source ~/.zsh/common.zsh
spike_cache_eval starship starship init zsh --print-full-init

# `sheldon source` output is cached; regenerated when plugins.toml or sheldon changes.
() {
  local toml=${XDG_CONFIG_HOME:-$HOME/.config}/sheldon/plugins.toml f=$SPIKE_CACHE/sheldon.zsh
  if [[ ! -s $f || $toml -nt $f || ${commands[sheldon]} -nt $f ]]; then
    mkdir -p -- $SPIKE_CACHE
    sheldon source >| $f && zcompile -R -- $f.zwc $f
  fi
  source $f
}
