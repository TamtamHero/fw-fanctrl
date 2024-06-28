#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
  exit 1
fi

HOME_DIR="$(eval echo "~$(logname)")"
INIT_SYSTEM="systemd"

# Argument parsing
SHORT=h
LONG=help,openrc
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--openrc')
        INIT_SYSTEM="openrc"
        ;;
    '--help' | '-h')
        echo "Usage: $0" 1>&2
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

if [ "${INIT_SYSTEM}"  = "systemd" ]; then
    SERVICES_DIR="./services"
    SERVICE_EXTENSION=".service"

    SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"

    echo "disabling services"
    systemctl daemon-reload
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "stopping [$SERVICE]"
        systemctl stop "$SERVICE" 2> "/dev/null" || true
        echo "disabling [$SERVICE]"
        systemctl disable "$SERVICE" 2> "/dev/null" || true
    done
elif [ "${INIT_SYSTEM}" = "openrc" ]; then
    echo "stopping fw-fanctrl"
    rc-service fw-fanctrl stop
    echo "diabling fw-fanctrl"
    rc-update del fw-fanctrl default
fi
