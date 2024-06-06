#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
  exit 1
fi

HOME_DIR="$(eval echo "~$(logname)")"

# Argument parsing
SHORT=d:,s:,h
LONG=dest-dir:,sysconf-dir:,openrc,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

DEST_DIR="/usr"
SYSCONF_DIR="/etc"
INIT_SYSTEM="systemd"


eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--dest-dir' | '-d')
        DEST_DIR=$2
        shift
        ;;
    '--sysconf-dir' | '-s')
        SYSCONF_DIR=$2
        shift
        ;;
   '--openrc')
        INIT_SYSTEM="openrc"
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--dest-dir,-d <installation destination directory (defaults to $DEST_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--openrc]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done
#

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

# move remaining legacy files
function move_legacy() {
    echo "moving legacy files to their new destination"
    (cp "$HOME_DIR/.config/fw-fanctrl"/* "$DEST_DIR$SYSCONF_DIR/fw-fanctrl/" && rm -rf "$HOME_DIR/.config/fw-fanctrl") 2> "/dev/null" || true
}

move_legacy

echo "enabling services"
if [ "${INIT_SYSTEM}"  = "systemd" ]; then
    SERVICES_DIR="./services"
    SERVICE_EXTENSION=".service"

    SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"

    systemctl daemon-reload
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "enabling [$SERVICE]"
        systemctl enable "$SERVICE"
        echo "starting [$SERVICE]"
        systemctl start "$SERVICE"
    done
elif [ "${INIT_SYSTEM}" = "openrc" ]; then
    echo "enabling fw-fanctrl"
    rc-update add fw-fanctrl default
    echo "starting fw-fanctrl"
    rc-service fw-fanctrl start
fi
