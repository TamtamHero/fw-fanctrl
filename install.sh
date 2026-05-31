#!/bin/bash
set -e

# Argument parsing
SHORT=r,p:,s:,h
LONG=remove,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-post-install,no-battery-sensors,no-sudo,manual-env,effective-installation-dir:,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

PREFIX_DIR="/usr"
SYSCONF_DIR="/etc"
SHOULD_INSTALL_ECTOOL=true
SHOULD_PRE_UNINSTALL=true
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false
IS_MANUAL_ENV=false
NO_BATTERY_SENSOR=false
NO_SUDO=false
EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=

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
    '--manual-env')
        IS_MANUAL_ENV=true
        ;;
    '--effective-installation-dir')
        EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-ectool] [--no-post-install] [--no-pre-uninstall] [--no-sudo] [--manual-env]" 1>&2
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

function initializeEnv() {
    echo "Initializing virtual environment"
    python3 -m venv .venv
    echo "Activating virtual environment"
    source .venv/bin/activate
    echo "Installing runtime and compilation dependencies"
    python3 -m pip install -e ".[compile]"
}

if ! python3 -h 1>/dev/null 2>&1; then
    echo "Missing package 'python3'!"
    exit 1
fi

if [ "$SHOULD_REMOVE" = false ]; then
    if [ "$IS_MANUAL_ENV" = false ]; then
        if ! python3 -m venv -h 1>/dev/null 2>&1; then
            echo "Missing python package 'venv'!"
            exit 1
        fi

        if [ "$IS_MANUAL_ENV" = false ]; then
            initializeEnv
        fi
    fi

    if ! python3 -m nuitka -h 1>/dev/null 2>&1; then
        echo "Missing python package 'Nuitka'!"
        exit 1
    fi

    if ! command -v patchelf 1>/dev/null 2>&1; then
        echo "Missing package 'patchelf'! Please install it from your distribution official repository."
        exit 1
    fi
fi

if [ "$NO_SUDO" = false ]; then
    sudo -v
fi

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

function build() {
    echo "building package"
    remove_target "dist/"
    python3 -m nuitka --onefile --follow-imports --include-package=fw_fanctrl --include-package-data=fw_fanctrl --output-dir=build/nuitka --output-filename=fw-fanctrl "main.py"
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2> "/dev/null" || true
}

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

function uninstall() {
    if [ "$SHOULD_PRE_UNINSTALL" = true ]; then
        PRE_UNINSTALL_ARGS=()
        if [ "$NO_SUDO" = true ]; then
            PRE_UNINSTALL_ARGS+=(--no-sudo)
        fi

        if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/pre-uninstall.sh "${PRE_UNINSTALL_ARGS[@]}"; then
            echo "Failed to run ./scripts/pre-uninstall.sh, aborting."
            echo "Be sure to give required administrative privileges."
            exit 1
        fi
    fi

    PRIVILEGED_UNINSTALL_ARGS=(
        --prefix-dir "$PREFIX_DIR"
        --sysconf-dir "$SYSCONF_DIR"
        --effective-installation-dir "$INSTALLATION_DIRECTORY"
    )
    if [ "$SHOULD_INSTALL_ECTOOL" = false ]; then
        PRIVILEGED_UNINSTALL_ARGS+=(--no-ectool)
    fi
    if [ "$NO_SUDO" = true ]; then
        PRIVILEGED_UNINSTALL_ARGS+=(--no-sudo)
    fi

    if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/privileged_uninstall.sh "${PRIVILEGED_UNINSTALL_ARGS[@]}"; then
        echo "Failed to run ./scripts/privileged_uninstall.sh, aborting"
        echo "Be sure to give required administrative privileges."
        exit 1
    fi
}

function install() {
    remove_target "dist/"

    if [ "$IS_MANUAL_ENV" = false ]; then
        initializeEnv
    fi

    build

    PRIVILEGED_INSTALL_ARGS=(
        --prefix-dir "$PREFIX_DIR"
        --sysconf-dir "$SYSCONF_DIR"
        --effective-installation-dir "$INSTALLATION_DIRECTORY"
    )
    if [ "$SHOULD_INSTALL_ECTOOL" = false ]; then
        PRIVILEGED_INSTALL_ARGS+=(--no-ectool)
    fi
    if [ "$SHOULD_PRE_UNINSTALL" = false ]; then
        PRIVILEGED_INSTALL_ARGS+=(--no-pre-uninstall)
    fi
    if [ "$NO_BATTERY_SENSOR" = true ]; then
        PRIVILEGED_INSTALL_ARGS+=(--no-battery-sensors)
    fi
    if [ "$NO_SUDO" = true ]; then
        PRIVILEGED_INSTALL_ARGS+=(--no-sudo)
    fi

    if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/privileged_install.sh "${PRIVILEGED_INSTALL_ARGS[@]}"; then
        echo "Failed to run ./scripts/privileged_install.sh, aborting"
        echo "Be sure to give required administrative privileges."
        exit 1
    fi

    if [ "$SHOULD_POST_INSTALL" = true ]; then
        POST_INSTALL_ARGS=(--sysconf-dir "$SYSCONF_DIR")
        if [ "$NO_SUDO" = true ]; then
            POST_INSTALL_ARGS+=(--no-sudo)
        fi

        if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/post-install.sh "${POST_INSTALL_ARGS[@]}"; then
            echo "Failed to run ./scripts/post-install.sh. Run the script with root permissions,"
            echo "or skip this step by using the --no-post-install option."
            exit 1
        fi
    fi
}

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0
