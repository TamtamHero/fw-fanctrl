#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
  exit 1
fi

HOME_DIR="$(eval echo "~$(logname)")"

# Argument parsing
SHORT=h
LONG=help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
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

SERVICES_DIR="./services/linux"
SERVICE_EXTENSION=".service"

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

echo "disabling services"
systemctl daemon-reload
for SERVICE in $SERVICES ; do
    SERVICE=$(sanitizePath "$SERVICE")
    echo "stopping [$SERVICE]"
    systemctl stop "$SERVICE" 2> "/dev/null" || true
    echo "disabling [$SERVICE]"
    systemctl disable "$SERVICE" 2> "/dev/null" || true
done
