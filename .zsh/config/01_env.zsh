alias zshenv="nano $0"

export PATH="$PATH:$HOME/.local/bin"

export EDITOR='nano'
export DOCKER_BUILDKIT=1

# load customisation
setopt nullglob
for envfile in ~/.env ~/.env.*; do
	[[ -f $envfile ]] || continue
	# Detect if envfile uses 'export' (ignoring comments and blank lines)
	if grep -E '^[[:space:]]*export[[:space:]]+' "$envfile" | grep -vq '^#'; then
		source "$envfile"
        echo finished loading $envfile
	else
		# shellcheck disable=SC2163
		while IFS= read -r line; do
			# Skip comments and blank lines
			[[ "$line" =~ ^[[:space:]]*# ]] && continue
			[[ -z "$line" ]] && continue
			# Export variable
			if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]]; then
				export "$line"
			fi
		done < "$envfile"
        echo DONE loading $envfile
	fi
done
unsetopt nullglob
