#!/bin/bash
set -e
source ./scripts/shared/common.sh

# Argument parsing
SHORT=r,p:,s:,h
LONG=remove,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-pre-install,no-post-install,no-sudo,manual-env,no-build,effective-installation-dir:,ignore-tool:,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

PREFIX_DIR="/usr"
SYSCONF_DIR="/etc"
IGNORED_TOOLS=()
SHOULD_PRE_UNINSTALL=true
SHOULD_PRE_INSTALL=true
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false
IS_MANUAL_ENV=false
SHOULD_BUILD=true
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
        # legacy
        IGNORED_TOOLS+=("ectool")
        ;;
    '--no-pre-uninstall')
        SHOULD_PRE_UNINSTALL=false
        ;;
    '--no-pre-install')
        SHOULD_PRE_INSTALL=false
        ;;
    '--no-post-install')
        SHOULD_POST_INSTALL=false
        ;;
    '--no-sudo')
        NO_SUDO=true
        ;;
    '--manual-env')
        IS_MANUAL_ENV=true
        ;;
    '--no-build')
        SHOULD_BUILD=false
        ;;
    '--effective-installation-dir')
        EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--ignore-tool')
        IGNORED_TOOLS+=("$2")
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s <system configuration destination directory (defaults to $SYSCONF_DIR)>] [--ignore-tool <tool id to ignore (e.g. 'framework_tool')>] [--no-pre-install] [--no-post-install] [--no-pre-uninstall] [--no-sudo] [--manual-env] [--no-build]" 1>&2
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

function check_requirements() {
    if [ "$NO_SUDO" = false ]; then
        sudo -v
        if ! sudo echo "sudo permissions granted"; then
            echo "Failed to gain sudo permissions"
            exit 1
        fi
        sudo -v
    fi
}

function uninstall() {
    if [ "$SHOULD_PRE_UNINSTALL" = true ]; then
        PRE_UNINSTALL_ARGS=()
        if [ "$NO_SUDO" = true ]; then
            PRE_UNINSTALL_ARGS+=(--no-sudo)
        fi

        if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/privileged_pre-uninstall.sh "${PRE_UNINSTALL_ARGS[@]}"; then
            echo "Failed to run ./scripts/privileged_pre-uninstall.sh, aborting."
            echo "Be sure to give required administrative privileges."
            exit 1
        fi
    fi

    PRIVILEGED_UNINSTALL_ARGS=(
        --prefix-dir "$PREFIX_DIR"
        --sysconf-dir "$SYSCONF_DIR"
        --effective-installation-dir "$INSTALLATION_DIRECTORY"
    )
    for TOOL in "${IGNORED_TOOLS[@]}"; do
        PRIVILEGED_UNINSTALL_ARGS+=(--ignore-tool "$TOOL")
    done
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
    if [ "$SHOULD_BUILD" = true ]; then
        BUILD_ARGS=()
        if [ "$IS_MANUAL_ENV" = true ]; then
            BUILD_ARGS+=(--manual-env)
        fi

        if ! sh ./scripts/build.sh "${BUILD_ARGS[@]}"; then
            echo "Failed to run ./scripts/build.sh, aborting."
            exit 1
        fi
    fi

    if [ "$SHOULD_PRE_INSTALL" = true ]; then
        PRE_INSTALL_ARGS=()
        if [ "$NO_SUDO" = true ]; then
            PRE_INSTALL_ARGS+=(--no-sudo)
        fi

        if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/privileged_pre-install.sh "${PRE_INSTALL_ARGS[@]}"; then
            echo "Failed to run ./scripts/privileged_pre-install.sh, aborting."
            echo "Be sure to give required administrative privileges."
            exit 1
        fi
    fi

    PRIVILEGED_INSTALL_ARGS=(
        --prefix-dir "$PREFIX_DIR"
        --sysconf-dir "$SYSCONF_DIR"
        --effective-installation-dir "$INSTALLATION_DIRECTORY"
    )
    for TOOL in "${IGNORED_TOOLS[@]}"; do
        PRIVILEGED_INSTALL_ARGS+=(--ignore-tool "$TOOL")
    done
    if [ "$NO_SUDO" = true ]; then
        PRIVILEGED_INSTALL_ARGS+=(--no-sudo)
    fi

    if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/privileged_install.sh "${PRIVILEGED_INSTALL_ARGS[@]}"; then
        echo "Failed to run ./scripts/privileged_install.sh, aborting"
        echo "Be sure to give required administrative privileges."
        exit 1
    fi

    if [ "$SHOULD_POST_INSTALL" = true ]; then
        POST_INSTALL_ARGS=()
        if [ "$NO_SUDO" = true ]; then
            POST_INSTALL_ARGS+=(--no-sudo)
        fi

        if ! $([ "$NO_SUDO" = false ] && printf 'sudo ') sh ./scripts/privileged_post-install.sh "${POST_INSTALL_ARGS[@]}"; then
            echo "Failed to run ./scripts/privileged_post-install.sh, aborting"
        echo "Be sure to give required administrative privileges."
        fi
    fi
}

check_requirements

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0
