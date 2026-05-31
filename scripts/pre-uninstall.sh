#!/bin/bash
set -e

# Argument parsing
NO_SUDO=false
SHORT=h
LONG=no-sudo,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--no-sudo')
        NO_SUDO=true
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--no-sudo]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done

if [ "$EUID" -ne 0 ] && [ "$NO_SUDO" = false ]
  then echo "This program requires root permissions or use the '--no-sudo' option"
  exit 1
fi

SERVICES_DIR="./services"
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
