#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "This program requires root permissions"
  exit 1
fi

# Argument parsing
SHORT=r,d:,p:,h
LONG=remove,dest-dir:,prefix-dir:,no-ectool,no-post-install,help
VALID_ARGS=$(getopt -a -n weather --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

PREFIX_DIR="/usr"
DEST_DIR="/usr"
SHOULD_INSTALL_ECTOOL=true
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--remove' | '-r')
        SHOULD_REMOVE=true
        ;;
    '--prefix-dir' | '-p')
        PREFIX_DIR=$2
        shift
        ;;
    '--dest-dir' | '-d')
        DEST_DIR=$2
        shift
        ;;
    '--no-ectool')
        SHOULD_INSTALL_ECTOOL=false
        ;;
    '--no-post-install')
        SHOULD_POST_INSTALL=false
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--dest-dir,-d <installation destination directory (defaults to $DEST_DIR)>] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--no-ectool] [--no-post-install]" 1>&2
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
    rm "/etc/systemd/system/fw-fanctrl.service" 2> "/dev/null" || true
}

function uninstall() {
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    systemctl daemon-reload
    for SERVICE in $SERVICES ; do
        # be EXTRA CAREFUL about the validity of the paths (dont wanna delete something important, right?... O_O)
        SERVICE=$(sanitizePath "$SERVICE")
        echo "stopping [$SERVICE]"
        systemctl stop "$SERVICE"
        echo "disabling [$SERVICE]"
        systemctl disable "$SERVICE"
        echo "removing '$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        (cd "$PREFIX_DIR/lib/systemd/system/" && rm -rf "$SERVICE$SERVICE_EXTENSION")
    done

    # remove program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "removing services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "removing sub-configurations for [$SERVICE]"
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "removing '$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG'"
            (cd "$PREFIX_DIR/lib/systemd/" && cd "$SERVICE" && rm -rf "$SUBCONFIG")
        done
    done

    rm "$DEST_DIR/bin/fw-fanctrl"
    ectool autofanctrl # restore default fan manager
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        rm "$DEST_DIR/bin/ectool"
    fi
    rm -rf "/etc/fw-fanctrl"

    uninstall_legacy
}

function install() {
    uninstall_legacy

    mkdir -p "$DEST_DIR/bin"
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        cp "./bin/ectool" "$DEST_DIR/bin/ectool"
        chmod +x "$DEST_DIR/bin/ectool"
    fi
    mkdir -p "/etc/fw-fanctrl"
    cp "./fanctrl.py" "$DEST_DIR/bin/fw-fanctrl"
    chmod +x "$DEST_DIR/bin/fw-fanctrl"

    cp -n "./config.json" "/etc/fw-fanctrl" 2> "/dev/null" || true

    # create program services based on the services present in the './services' folder
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        if [ "$(systemctl is-active "$SERVICE")" == "active" ]; then
            echo "stopping [$SERVICE]"
            systemctl stop "$SERVICE"
        fi
        echo "creating '$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%PREFIX_DIRECTORY%/${PREFIX_DIR//\//\\/}/" | tee "$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
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
            echo "creating '$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG_FOLDER'"
            (cd "$PREFIX_DIR/lib/systemd/" && cd "$SERVICE" && mkdir -p "$SUBCONFIG_FOLDER")
        done
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        # add sub-configurations
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "adding '$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG'"
            cat "$SERVICES_DIR/$SERVICE/$SUBCONFIG" | sed -e "s/%PREFIX_DIRECTORY%/${PREFIX_DIR//\//\\/}/" | tee "$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG" > "/dev/null"
            chmod +x "$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG"
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