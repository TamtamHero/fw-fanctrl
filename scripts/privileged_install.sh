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

TEMP_FOLDER='./.temp'
trap 'rm -rf $TEMP_FOLDER' EXIT

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

function install_tool() {
    workingDirectory="$1"
    toolId="$2"
    toolDestPath="$3/$toolId"

    echo "Installing $toolId"

    toolTargetUrl="$(awk '{$1=$1; print}' "./fetch/$toolId/linux/target.url")"
    toolReleaseVersion="$(awk '{$1=$1; print}' "./fetch/$toolId/linux/release.version")"
    toolSha256Hash="$(awk '{$1=$1; print}' "./fetch/$toolId/linux/sha256.hash")"

    if [ -z "$toolTargetUrl" ] || [ -z "$toolReleaseVersion" ] || [ -z "$toolSha256Hash" ]; then
      echo "Failed to gather necessary data for $toolId"
      return 1
    fi

    artifactPath="$workingDirectory/$toolId"

    curl -s -S -o "$artifactPath" -L "$(echo "$toolTargetUrl" | sed -e "s/%RELEASE_VERSION%/${toolReleaseVersion//\//\\/}/")" || (echo "failed to download the artifact." && return 1)
    if [[ $? -ne 0 ]]; then return 1; fi

    echo "checking artifact sha256 sum"
    echo "$toolSha256Hash $artifactPath" | sha256sum --check --status
    if [[ $? -ne 0 ]]; then
      echo "Incorrect sha256 sum for $toolId artifact '$toolReleaseVersion' : target '$toolSha256Hash' != actual '$(sha256sum "$artifactPath" | cut -d ' ' -f 1)'"
      return 1
    fi
    echo "Valid $toolId checksum '$toolSha256Hash'"

    cp "$artifactPath" "$toolDestPath" &&
    chmod +x "$toolDestPath"

    echo "$toolId installed at '$toolDestPath'"
}

function install_framework_tool() {
    install_tool "$1" "framework_tool" "$PREFIX_DIR/bin"
}

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"

function privileged_install() {
    uninstall_legacy

    remove_target "$TEMP_FOLDER"
    mkdir -p "$PREFIX_DIR/bin"

    if ! contains "framework_tool" "${IGNORED_TOOLS[@]}"; then
        mkdir "$TEMP_FOLDER"
        install_framework_tool "$TEMP_FOLDER" || (echo "an error occurred when installing framework_tool." && echo "please check your internet connection or consider installing it manually and using '--ignore-tool framework_tool' on the installation script." && exit 1)
        remove_target "$TEMP_FOLDER"
    fi
    mkdir -p "$SYSCONF_DIR/fw-fanctrl"

    cp "./build/nuitka/fw-fanctrl" "$EXECUTABLE_INSTALLATION_PATH"
    chmod +x "$EXECUTABLE_INSTALLATION_PATH"

    cp -pn "./src/fw_fanctrl/_resources/config.json" "$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true
    cp -f "./src/fw_fanctrl/_resources/config.schema.json" "$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true

    echo "creating '$PREFIX_DIR/lib/systemd/system'"
    mkdir -p "$PREFIX_DIR/lib/systemd/system"
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "creating '$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%EXECUTABLE_INSTALLATION_PATH%/${EXECUTABLE_INSTALLATION_PATH//\//\\/}/" | sed -e "s/%SYSCONF_DIRECTORY%/${SYSCONF_DIR//\//\\/}/" | tee "$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
    done
}

privileged_install
