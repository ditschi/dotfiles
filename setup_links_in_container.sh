#!/bin/bash
if [ ! -f /.dockerenv ]; then
    echo "Not inside a container, not creating links"
    exit
fi

set -Eeuo pipefail
SCRIPTDIR=$(dirname "$0")

mkdir -p ~/.local/
SYMLINK_PATHS=( ".local/share" ".gitconfig" ".zshrc" ".zsh" ".env" ".p10k.zsh" ".zsh_history" ".cache" )

echo Creating symlinks to mounted HOME from host machine
MOUNT_PATH_IN_CONTAINER=$SCRIPTDIR
for path in ${SYMLINK_PATHS[@]}; do
    SOURCE_PATH="$MOUNT_PATH_IN_CONTAINER/$path"
    if [ -f $SOURCE_PATH ] || [ -d $SOURCE_PATH ]; then
        ln -sf $SOURCE_PATH ~/$path || echo Issue creating link for ~/$path
    else
        echo "Path to link not found: '$SOURCE_PATH'"
    fi
done


EXTENSION_PATH="$MOUNT_PATH_IN_CONTAINER/setup_additional_links_in_container.sh"
if [ -f $EXTENSION_PATH ]; then
    ./$EXTENSION_PATH
else
    echo "Extension point for creating links not used. If needed create it at $EXTENSION_PATH"
fi
