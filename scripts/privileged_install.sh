#!/bin/bash
set -e

PREFIX_DIR="/usr"
SYSCONF_DIR="/etc"
SHOULD_INSTALL_ECTOOL=true
SHOULD_PRE_UNINSTALL=true
NO_BATTERY_SENSOR=false
NO_SUDO=false
EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=

SHORT=p:,s:,h
LONG=prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-battery-sensors,no-sudo,effective-installation-dir:,help
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
    '--no-pre-uninstall')
        SHOULD_PRE_UNINSTALL=false
        ;;
    '--no-battery-sensors')
        NO_BATTERY_SENSOR=true
        ;;
    '--no-sudo')
        NO_SUDO=true
        ;;
    '--effective-installation-dir')
        EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-ectool] [--no-pre-uninstall] [--no-battery-sensors] [--no-sudo] [--effective-installation-dir <directory (defaults to [prefix-dir]/bin)>]" 1>&2
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

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"

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

function installEctool() {
    workingDirectory=$1
    echo "installing ectool"

    ectoolDestPath="$PREFIX_DIR/bin/ectool"

    ectoolJobId="$(cat './fetch/ectool/linux/gitlab_job_id')"
    ectoolSha256Hash="$(cat './fetch/ectool/linux/hash.sha256')"

    artifactsZipFile="$workingDirectory/artifact.zip"

    echo "downloading artifact from gitlab"
    curl -s -S -o "$artifactsZipFile" -L "https://gitlab.howett.net/DHowett/ectool/-/jobs/${ectoolJobId}/artifacts/download?file_type=archive" || (echo "failed to download the artifact." && return 1)
    if [[ $? -ne 0 ]]; then return 1; fi

    echo "checking artifact sha256 sum"
    actualEctoolSha256Hash=$(sha256sum "$artifactsZipFile" | cut -d ' ' -f 1)
    if [[ "$actualEctoolSha256Hash" != "$ectoolSha256Hash" ]]; then
        echo "Incorrect sha256 sum for ectool gitlab artifact '$ectoolJobId' : '$ectoolSha256Hash' != '$actualEctoolSha256Hash'"
        return 1
    fi

    echo "extracting artifact"
    {
        unzip -q -j "$artifactsZipFile" '_build/src/ectool' -d "$workingDirectory" &&
        cp "$workingDirectory/ectool" "$ectoolDestPath" &&
        chmod +x "$ectoolDestPath"
    } || (echo "failed to extract the artifact to its designated location." && return 1)
    if [[ $? -ne 0 ]]; then return 1; fi

    echo "ectool installed"
}

function privileged_install() {
    remove_target "$TEMP_FOLDER"
    uninstall_legacy

    mkdir -p "$PREFIX_DIR/bin"

    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        mkdir "$TEMP_FOLDER"
        installEctool "$TEMP_FOLDER" || (echo "an error occurred when installing ectool." && echo "please check your internet connection or consider installing it manually and using --no-ectool on the installation script." && exit 1)
        remove_target "$TEMP_FOLDER"
    fi
    mkdir -p "$SYSCONF_DIR/fw-fanctrl"

    cp "./build/nuitka/fw-fanctrl" "$EXECUTABLE_INSTALLATION_PATH"
    chmod +x "$EXECUTABLE_INSTALLATION_PATH"

    cp -pn "./src/fw_fanctrl/_resources/config.json" "$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true
    cp -f "./src/fw_fanctrl/_resources/config.schema.json" "$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true

    # add --no-battery-sensors flag to the fanctrl service if specified
    if [ "$NO_BATTERY_SENSOR" = true ]; then
        NO_BATTERY_SENSOR_OPTION="--no-battery-sensors"
    fi

    # create program services based on the services present in the './services' folder
    echo "creating '$PREFIX_DIR/lib/systemd/system'"
    mkdir -p "$PREFIX_DIR/lib/systemd/system"
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        if [ "$SHOULD_PRE_UNINSTALL" = true ] && [ "$(systemctl is-active "$SERVICE")" == "active" ]; then
            echo "stopping [$SERVICE]"
            systemctl stop "$SERVICE"
        fi
        echo "creating '$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%EXECUTABLE_INSTALLATION_PATH%/${EXECUTABLE_INSTALLATION_PATH//\//\\/}/" | sed -e "s/%SYSCONF_DIRECTORY%/${SYSCONF_DIR//\//\\/}/" | sed -e "s/%NO_BATTERY_SENSOR_OPTION%/${NO_BATTERY_SENSOR_OPTION}/" | tee "$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
    done
}

privileged_install
