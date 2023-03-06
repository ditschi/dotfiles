#!/bin/bash
 
set -e
 
BOSCH_BASE_SERVER='\\bosch.com\dfsrb'
 
VERSION='1.0'
USER="$USER"
WORKGROUP='DE'
 
MNTDIR="/tmp/mnt"
MNTBASEDIR="${MNTDIR}/bosch.com/dfsrb"
 
function usage(){
    >&2 echo "Usage: dfs.sh [OPTIONS] [LINK]"
    >&2 echo "OPTIONS:"
    >&2 echo "    -clip         Use link from xClipboard"
    >&2 echo "    -u            Unmount all mounted directories"
    >&2 echo "    --help        Print this help"
}
 
function isBaseMounted(){
    mount | grep -q "${BOSCH_BASE_SERVER//\\/\\\\}"
}
 
function umountBase(){
    if isBaseMounted; then
        sudo umount "$BOSCH_BASE_SERVER"
        # delete empty directories
        for d in $(find $MNTDIR -type d | tac); do
            rmdir $d || true
        done
    else
        >&2 echo "Already unmounted!"
    fi
}
 
function mountLink() {
    link=$1
    [[ -z $link ]] && usage && exit 1
    [[ -z $(echo $link | grep "${BOSCH_BASE_SERVER//\\/\\\\}") ]] && >&2 echo "Error: Invalid link $link" && usage && exit 1
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
            >&2 echo "Using link from clipboard: $link"
            ;;
        "--help")
            usage
            exit 0
            ;;
        "-u")
            CMD="umountBase"
            ;;
        *)
            [[ -n $link ]] && >&2 echo "Error: Multiple links given!" && usage && exit 1
            link="$1"
            ;;
    esac
    shift
done
${CMD:-mountLink} $link
