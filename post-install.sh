#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
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

echo "enabling services"
sudo systemctl daemon-reload
for SERVICE in $SERVICES ; do
    SERVICE=$(sanitizePath "$SERVICE")
    echo "enabling [$SERVICE]"
    sudo systemctl enable "$SERVICE"
    echo "starting [$SERVICE]"
    sudo systemctl start "$SERVICE"
done
