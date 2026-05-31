#!/bin/bash
set -e

PREFIX_DIR="/usr"
SYSCONF_DIR="/etc"
SHOULD_INSTALL_ECTOOL=true
NO_SUDO=false
EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=

SHORT=p:,s:,h
LONG=prefix-dir:,sysconf-dir:,no-ectool,no-sudo,effective-installation-dir:,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--prefix-dir' | '-p')
        PREFIX_DIR=$2
        shift
        ;;
    '--sysconf-dir' | '-s')
        SYSCONF_DIR=$2
        shift
        ;;
    '--no-ectool')
        SHOULD_INSTALL_ECTOOL=false
        ;;
    '--no-sudo')
        NO_SUDO=true
        ;;
    '--effective-installation-dir')
        EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-ectool] [--no-sudo] [--effective-installation-dir <directory (defaults to [prefix-dir]/bin)>]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done

INSTALLATION_DIRECTORY="$PREFIX_DIR/bin"
if [ -n "$EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE" ]; then
    INSTALLATION_DIRECTORY=$EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE
fi

EXECUTABLE_INSTALLATION_PATH="$INSTALLATION_DIRECTORY/fw-fanctrl"

if [ "$EUID" -ne 0 ] && [ "$NO_SUDO" = false ]; then
    echo "This program requires root permissions or use the '--no-sudo' option"
    exit 1
fi

SERVICES_DIR="./services"
SERVICE_EXTENSION=".service"

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"
SERVICES_SUBCONFIGS="$(cd "$SERVICES_DIR" && find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)"

# safe remove function
function remove_target() {
    local target="$1"
    if [ -e "$target" ] || [ -L "$target" ]; then
        if ! rm -rf "$target" 2> "/dev/null"; then
            echo "Failed to remove: $target"
            echo "Please run:"
            echo "    sudo ./install.sh --remove"
            exit 1
        fi
    fi
}

# remove remaining legacy files
function uninstall_legacy() {
    echo "removing legacy files"
    remove_target "/usr/local/bin/fw-fanctrl"
    remove_target "/usr/local/bin/ectool"
    remove_target "/usr/local/bin/fanctrl.py"
    remove_target "/etc/systemd/system/fw-fanctrl.service"
    remove_target "$PREFIX_DIR/bin/fw-fanctrl"
}

function privileged_uninstall() {
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        # be EXTRA CAREFUL about the validity of the paths (dont wanna delete something important, right?... O_O)
        remove_target "$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION"
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
            remove_target "$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG"
        done
    done

    rm -f "$EXECUTABLE_INSTALLATION_PATH"

    ectool autofanctrl 2> "/dev/null" || true # restore default fan manager
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        remove_target "$PREFIX_DIR/bin/ectool"
    fi
    remove_target "$SYSCONF_DIR/fw-fanctrl"
    remove_target "/run/fw-fanctrl"

    uninstall_legacy
}

privileged_uninstall
