#!/bin/bash
set -e

# Argument parsing
SHORT=r,d:,p:,s:,h
LONG=remove,dest-dir:,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-post-install,no-battery-sensors,no-sudo,no-pip-install,pipx,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

TEMP_FOLDER='./.temp'
trap 'rm -rf $TEMP_FOLDER' EXIT

PREFIX_DIR="/usr"
DEST_DIR=""
SYSCONF_DIR=
SHOULD_INSTALL_ECTOOL=
SHOULD_PRE_UNINSTALL=
SHOULD_POST_INSTALL=
NO_BATTERY_SENSOR=
NO_SUDO=
SHOULD_REMOVE=false
NO_PIP_INSTALL=false
PIPX=false

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
    '--sysconf-dir' | '-s')
        SYSCONF_DIR=$2
        shift
        ;;
    '--no-ectool')
        SHOULD_INSTALL_ECTOOL=false
        ;;
    '--no-pre-uninstall')
        SHOULD_PRE_UNINSTALL=false
        ;;
    '--no-post-install')
        SHOULD_POST_INSTALL=false
        ;;
    '--no-battery-sensors')
        NO_BATTERY_SENSOR=true
        ;;
    '--no-sudo')
        NO_SUDO=true
        ;;
    '--no-pip-install')
        NO_PIP_INSTALL=true
        ;;
    '--pipx')
        PIPX=true
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--dest-dir,-d <installation destination directory (defaults to $DEST_DIR)>] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-ectool] [--no-post-install] [--no-pre-uninstall] [--no-sudo] [--no-pip-install] [--pipx]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done

if ! python -h 1>/dev/null 2>&1; then
    echo "Missing package 'python'!"
    exit 1
fi

if [ "$NO_PIP_INSTALL" = false ]; then
    if ! python -m pip -h 1>/dev/null 2>&1; then
        echo "Missing python package 'pip'!"
        exit 1
    fi
fi

if [ "$PIPX" = true ]; then
    if ! pipx -h >/dev/null 2>&1; then
        echo "Missing package 'pipx'!"
        exit 1
    fi
fi

if [ "$SHOULD_REMOVE" = false ]; then
    if ! python -m build -h 1>/dev/null 2>&1; then
        echo "Missing python package 'build'!"
        exit 1
    fi
fi

# Root check
if [ "$EUID" -ne 0 ] && [ "$NO_SUDO" = false ]; then
    echo "This program requires root permissions or use the '--no-sudo' option"
    exit 1
fi

function generate_args() {
    ARGS=()

    if [ "$SHOULD_REMOVE" == "true" ]; then
        ARGS+=("--remove")
    fi
    if [ -n "$PREFIX_DIR" ]; then
        ARGS+=("--prefix-dir=$(printf '%q' "$PREFIX_DIR")")
    fi
    if [ -n "$DEST_DIR" ]; then
        ARGS+=("--dest-dir=$(printf '%q' "$DEST_DIR")")
    fi
    if [ -n "$SYSCONF_DIR" ]; then
        ARGS+=("--sysconf-dir=$(printf '%q' "$SYSCONF_DIR")")
    fi
    if [ "$NO_SUDO" == "true" ]; then
        ARGS+=("--no-sudo")
    fi
    if [ "$SHOULD_INSTALL_ECTOOL" == "false" ]; then
        ARGS+=("--no-ectool")
    fi
    if [ "$SHOULD_PRE_UNINSTALL" == "false" ]; then
        ARGS+=("--no-pre-uninstall")
    fi
    if [ "$SHOULD_POST_INSTALL" == "false" ]; then
        ARGS+=("--no-post-install")
    fi
    if [ "$NO_BATTERY_SENSOR" == "true" ]; then
        ARGS+=("--no-battery-sensors")
    fi
    if [ "$PIPX" == "true" ]; then
        ARGS+=("--pipx")
    fi
    ARGS+=("--executable-path=$(printf '%q' "$(which 'fw-fanctrl')")")

    echo "${ARGS[*]}"
}

function uninstall() {
    echo "$@"
    if "fw-fanctrl-setup" -h 1>/dev/null 2>&1; then
        "fw-fanctrl-setup" run $(generate_args) "$@"
        if [[ $? -ne 0 ]]; then
            echo "Failed to uninstall the existing version correctly."
            echo "Please seek further assistance, or delete the remaining files manually,"
            echo "and then uninstall the 'fw-fanctrl' python module with 'python -m pip uninstall -y fw-fanctrl'."
            exit 1;
        fi
    fi

    if [ "$NO_PIP_INSTALL" = false ]; then
        echo "Uninstalling python package"
        if [ "$PIPX" = false ]; then
            python -m pip uninstall -y fw-fanctrl 2> "/dev/null" || true
        else
            pipx --global uinistall fw-fanctrl 2> "/dev/null" || true
        fi
    fi
}

function build() {
    echo "Building package"
    rm -rf "dist/" 2> "/dev/null" || true
    python -m build -s
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2> "/dev/null" || true
}

function cleanup() {
    echo "Cleanup"
    rm -rf "dist/" 2> "/dev/null" || true
}

function install() {
    uninstall --keep-config

    build

    if [ "$NO_PIP_INSTALL" = false ]; then
        echo "Installing python package"
        if [ "$PIPX" = false ]; then
            python -m pip install --prefix="$DEST_DIR$PREFIX_DIR" dist/*.tar.gz
            which python
        else
            pipx install --global --force dist/*.tar.gz
        fi
    fi

    cleanup

    echo "Script installation path is '$(which 'fw-fanctrl')'"
    echo "Script installation setup path is '$(which 'fw-fanctrl-setup')'"

    "fw-fanctrl-setup" run $(generate_args)
}

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0
