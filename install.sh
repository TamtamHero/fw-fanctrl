#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
  exit 1
fi

LOGNAME="$(logname)"
USER="$LOGNAME"
HOME="$(eval echo "~$USER")"

SERVICES_DIR="./services"
SERVICE_EXTENSION=".service"

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"
SERVICES_SUBCONFIGS="$(cd "$SERVICES_DIR" && find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)"

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

function uninstall() {
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    for SERVICE in $SERVICES ; do
        # be EXTRA CAREFUL about the validity of the paths (dont wanna delete something important, right?... O_O)
        SERVICE=$(sanitizePath "$SERVICE")
        sudo systemctl daemon-reload
        echo "stopping [$SERVICE]"
        sudo systemctl stop "$SERVICE"
        echo "disabling [$SERVICE]"
        sudo systemctl disable "$SERVICE"
        echo "removing '/etc/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        (cd "/etc/systemd/system/" && sudo rm -rf "$SERVICE$SERVICE_EXTENSION")
    done

    # remove program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "removing services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "removing sub-configurations for [$SERVICE]"
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "removing '/usr/lib/systemd/$SERVICE/$SUBCONFIG'"
            (cd "/usr/lib/systemd/" && cd "$SERVICE" && rm -rf "$SUBCONFIG")
        done
    done

    rm "/usr/local/bin/fw-fanctrl"
    ectool autofanctrl # restore default fan manager
    rm "/usr/local/bin/ectool"
    rm -rf "$HOME/.config/fw-fanctrl"
}

function install() {
    if [ "$1" != "--no-requirements" ]; then
        pip3 install -r requirements.txt || exit 1
    fi
    cp "./bin/ectool" "/usr/local/bin"
    cp "./fanctrl.py" "/usr/local/bin/fw-fanctrl"
    chmod +x "/usr/local/bin/fw-fanctrl"
    chown "$LOGNAME:$LOGNAME" "/usr/local/bin/fw-fanctrl"
    mkdir -p "$HOME/.config/fw-fanctrl"
    cp -n "./config.json" "$HOME/.config/fw-fanctrl/" || true

    # cleaning legacy file
    rm "/usr/local/bin/fanctrl.py" 2> "/dev/null" || true

    # create program services based on the services present in the './services' folder
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        if [ "$(sudo systemctl is-active "$SERVICE")" == "active" ]; then
            echo "stopping [$SERVICE]"
            sudo systemctl stop "$SERVICE"
        fi
        echo "creating '/etc/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        # 'envsubst' replace environment variables in the service file
        envsubst < "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sudo tee "/etc/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
        sudo systemctl daemon-reload
        echo "enabling [$SERVICE]"
        sudo systemctl enable "$SERVICE"
        echo "starting [$SERVICE]"
        sudo systemctl start "$SERVICE"
    done

    # add program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "adding services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "adding sub-configurations for [$SERVICE]"
        SUBCONFIG_FOLDERS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)"
        # ensure folders exists
        for SUBCONFIG_FOLDER in $SUBCONFIG_FOLDERS ; do
            SUBCONFIG_FOLDER=$(sanitizePath "$SUBCONFIG_FOLDER")
            echo "creating '/usr/lib/systemd/$SERVICE/$SUBCONFIG_FOLDER'"
            (cd "/usr/lib/systemd/" && cd "$SERVICE" && sudo mkdir -p "$SUBCONFIG_FOLDER")
        done
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        # add sub-configurations
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "adding '/usr/lib/systemd/$SERVICE/$SUBCONFIG'"
            sudo cp -f "$SERVICES_DIR/$SERVICE/$SUBCONFIG" "/usr/lib/systemd/$SERVICE/$SUBCONFIG"
            sudo chmod +x "/usr/lib/systemd/$SERVICE/$SUBCONFIG"
        done
    done
}

if [ "$1" = "remove" ]; then
    uninstall
elif [[ "$1" =~ ^$|^-- ]]; then
    install "$1"
else
    echo "Unknown command '$1'"
    exit 1
fi
exit 0