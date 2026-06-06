#!/bin/bash
set -e
source ./scripts/shared/common.sh

PREFIX_DIR="/usr"
SYSCONF_DIR="/etc"
IGNORED_TOOLS=()
NO_SUDO=false
EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=

SHORT=p:,s:,h
LONG=prefix-dir:,sysconf-dir:,no-sudo,effective-installation-dir:,ignore-tool:,help
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
    '--ignore-tool')
        IGNORED_TOOLS+=("$2")
        shift
        ;;
    '--no-sudo')
        NO_SUDO=true
        ;;
    '--effective-installation-dir')
        EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-sudo] [--effective-installation-dir <directory (defaults to [prefix-dir]/bin)>] [--ignore-tool <tool id to ignore (e.g. 'framework_tool')>]" 1>&2
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

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"

function privileged_uninstall() {
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        remove_target "$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION"
    done

    remove_target "$EXECUTABLE_INSTALLATION_PATH"

    reset_tool "framework_tool" "$PREFIX_DIR/bin"
    if ! contains "framework_tool" "${IGNORED_TOOLS[@]}"; then
        uninstall_tool "framework_tool" "$PREFIX_DIR/bin"
    fi

    remove_target "$SYSCONF_DIR/fw-fanctrl"
    remove_target "/run/fw-fanctrl"

    uninstall_legacy
}

privileged_uninstall
