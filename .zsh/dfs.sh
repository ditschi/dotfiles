#!/bin/bash

set -e

BOSCH_BASE_SERVER='\\bosch.com\dfsrb'

VERSION='1.0'
USER="$USER"
WORKGROUP='DE'

MNTDIR="/tmp/mnt"
MNTBASEDIR="${MNTDIR}/bosch.com/dfsrb"

function usage() {
    echo >&2 "Usage: dfs.sh [OPTIONS] [LINK]"
    echo >&2 "OPTIONS:"
    echo >&2 "    -clip         Use link from xClipboard"
    echo >&2 "    -u            Unmount all mounted directories"
    echo >&2 "    --help        Print this help"
}

function isBaseMounted() {
    mount | grep -q "${BOSCH_BASE_SERVER//\\/\\\\}"
}

function umountBase() {
    if isBaseMounted; then
        sudo umount "$BOSCH_BASE_SERVER"
        # delete empty directories
        for d in $(find $MNTDIR -type d | tac); do
            rmdir $d || true
        done
    else
        echo >&2 "Already unmounted!"
    fi
}

function mountLink() {
    link=$1
    [[ -z $link ]] && usage && exit 1
    [[ -z $(echo $link | grep "${BOSCH_BASE_SERVER//\\/\\\\}") ]] && echo >&2 "Error: Invalid link $link" && usage && exit 1
    target=${link//"${BOSCH_BASE_SERVER}\\"/}
    path=${target//\\/\/}
    if ! isBaseMounted; then
        mkdir -p $MNTBASEDIR
        sudo mount.cifs "$BOSCH_BASE_SERVER" "$MNTBASEDIR" -o username=${USER},workgroup=${WORKGROUP},vers=${VERSION}
    fi
    echo "$MNTBASEDIR/$path"
}

while [ $# -gt 0 ]; do
    case $1 in
    "-clip")
        link=$(xclip -out)
        echo >&2 "Using link from clipboard: $link"
        ;;
    "--help")
        usage
        exit 0
        ;;
    "-u")
        CMD="umountBase"
        ;;
    *)
        [[ -n $link ]] && echo >&2 "Error: Multiple links given!" && usage && exit 1
        link="$1"
        ;;
    esac
    shift
done
${CMD:-mountLink} $link
