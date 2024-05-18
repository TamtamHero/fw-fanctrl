#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
  exit 1
fi

# Argument parsing
SHORT=r,d:,h
LONG=remove,install-dir:,no-post-install,help
VALID_ARGS=$(getopt -a -n weather --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

INSTALL_DIRECTORY="/usr/bin"
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--remove' | '-r')
        SHOULD_REMOVE=true
        ;;
    '--install-dir' | '-d')
        INSTALL_DIRECTORY=$2
        shift
        ;;
    '--no-post-install')
        SHOULD_POST_INSTALL=false
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--install-dir,-d <install directory (defaults to $INSTALL_DIRECTORY)>] [--no-post-install]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done
#

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

# remove remaining legacy files
function uninstall_legacy() {
    rm "/usr/local/bin/fw-fanctrl" 2> "/dev/null" || true
    rm "/usr/local/bin/ectool" 2> "/dev/null" || true
    rm "/usr/local/bin/fanctrl.py" 2> "/dev/null" || true
}

function uninstall() {
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    sudo systemctl daemon-reload
    for SERVICE in $SERVICES ; do
        # be EXTRA CAREFUL about the validity of the paths (dont wanna delete something important, right?... O_O)
        SERVICE=$(sanitizePath "$SERVICE")
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

    rm "$INSTALL_DIRECTORY/fw-fanctrl"
    ectool autofanctrl # restore default fan manager
    rm "$INSTALL_DIRECTORY/ectool"
    rm -rf "/etc/fw-fanctrl"

    uninstall_legacy
}

function install() {
    uninstall_legacy

    mkdir -p "$INSTALL_DIRECTORY"
    cp "./bin/ectool" "$INSTALL_DIRECTORY/ectool"
    cp "./fanctrl.py" "$INSTALL_DIRECTORY/fw-fanctrl"
    chmod +x "$INSTALL_DIRECTORY/ectool"
    chmod +x "$INSTALL_DIRECTORY/fw-fanctrl"
    mkdir -p "/etc/fw-fanctrl"

    cp -n "./config.json" "/etc/fw-fanctrl" 2> "/dev/null" || true

    # create program services based on the services present in the './services' folder
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        if [ "$(sudo systemctl is-active "$SERVICE")" == "active" ]; then
            echo "stopping [$SERVICE]"
            sudo systemctl stop "$SERVICE"
        fi
        echo "creating '/etc/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%DIRECTORY%/${INSTALL_DIRECTORY//\//\\/}/" | sudo tee "/etc/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
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
            cat "$SERVICES_DIR/$SERVICE/$SUBCONFIG" | sed -e "s/%DIRECTORY%/${INSTALL_DIRECTORY//\//\\/}/" | sudo tee "/usr/lib/systemd/$SERVICE/$SUBCONFIG" > "/dev/null"
            sudo chmod +x "/usr/lib/systemd/$SERVICE/$SUBCONFIG"
        done
    done
    if [ "$SHOULD_POST_INSTALL" = true ]; then
        sh "./post-install.sh"
    fi
}

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0