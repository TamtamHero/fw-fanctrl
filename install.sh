#!/bin/bash
set -e

# Argument parsing
SHORT=r,d:,p:,s:,h
LONG=remove,dest-dir:,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-post-install,no-battery-sensors,no-sudo,atomic,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

TEMP_FOLDER='./.temp'
trap 'rm -rf $TEMP_FOLDER' EXIT

PREFIX_DIR="/usr"
DEST_DIR=""
SYSCONF_DIR="/etc"
SHOULD_INSTALL_ECTOOL=true
SHOULD_PRE_UNINSTALL=true
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false
NO_BATTERY_SENSOR=false
NO_SUDO=false
ATOMIC=true

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
    '--atomic')
        ATOMIC=true
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--dest-dir,-d <installation destination directory (defaults to $DEST_DIR)>] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-ectool] [--no-post-install] [--no-pre-uninstall] [--no-sudo]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done

# Root check
if [ "$EUID" -ne 0 ] && [ "$NO_SUDO" = false ]
  then echo "This program requires root permissions or use the '--no-sudo' option"
  exit 1
fi

# set the directories
BIN_DIR="$DEST_DIR$PREFIX_DIR/bin"
ETC_DIR="$DEST_DIR$SYSCONF_DIR"
LIB_DIR="$DEST_DIR$PREFIX_DIR/lib"
SERVICES_DIR="./services"
SERVICE_EXTENSION=".service"

SERVICES="$(cd "$SERVICES_DIR" && find . -maxdepth 1 -maxdepth 1 -type f -name "*$SERVICE_EXTENSION" -exec basename {} "$SERVICE_EXTENSION" \;)"
SERVICES_SUBCONFIGS="$(cd "$SERVICES_DIR" && find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)"

# if atomic flag is set
if [ "$ATOMIC" = true ]; then
  # override the destination directories
  BIN_DIR="/var/usrlocal/bin"
  ETC_DIR="/etc"
  LIB_DIR="/etc"
fi

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

# remove remaining legacy files
function uninstall_legacy() {
    echo "removing legacy files"
    rm "/usr/local/bin/fw-fanctrl" 2> "/dev/null" || true
    rm "/usr/local/bin/ectool" 2> "/dev/null" || true
    rm "/usr/local/bin/fanctrl.py" 2> "/dev/null" || true
    rm "/etc/systemd/system/fw-fanctrl.service" 2> "/dev/null" || true
}

function uninstall() {
    if [ "$SHOULD_PRE_UNINSTALL" = true ]; then
        ./pre-uninstall.sh "$([ "$NO_SUDO" = true ] && echo "--no-sudo")"
    fi
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        # be EXTRA CAREFUL about the validity of the paths (dont wanna delete something important, right?... O_O)
        rm -rf "$LIB_DIR/systemd/system/$SERVICE$SERVICE_EXTENSION"
    done

    # remove program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "removing services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "removing sub-configurations for [$SERVICE]"
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "removing '$LIB_DIR/systemd/$SERVICE/$SUBCONFIG'"
            rm -rf "$LIB_DIR/systemd/$SERVICE/$SUBCONFIG" 2> "/dev/null" || true
        done
    done

    rm "$BIN_DIR/fw-fanctrl" 2> "/dev/null" || true
    ectool autofanctrl 2> "/dev/null" || true # restore default fan manager
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        rm "$BIN_DIR/ectool" 2> "/dev/null" || true
    fi
    rm -rf "$ETC_DIR/fw-fanctrl" 2> "/dev/null" || true
    rm -rf "/run/fw-fanctrl" 2> "/dev/null" || true

    uninstall_legacy
}

function install() {
    uninstall_legacy

    # remove the temporary folder if it exists
    rm -rf "$TEMP_FOLDER"

    # install ectool if specified
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        mkdir "$TEMP_FOLDER"
        installEctool "$TEMP_FOLDER" || (echo "an error occurred when installing ectool." && echo "please check your internet connection or consider installing it manually and using --no-ectool on the installation script." && exit 1)
        rm -rf "$TEMP_FOLDER"
    fi

    # install the fanctrl program in the bin directory
    mkdir -p $BIN_DIR
    cp "./fanctrl.py" "$BIN_DIR/fw-fanctrl"
    chmod +x "$BIN_DIR/fw-fanctrl"

    # copy the fanctrl configuration in the etc directory
    mkdir -p "$ETC_DIR/fw-fanctrl"
    cp -n "./config.json" "$ETC_DIR/fw-fanctrl" 2> "/dev/null" || true

    # add --no-battery-sensors flag to the fanctrl service if specified
    if [ "$NO_BATTERY_SENSOR" = true ]; then
        NO_BATTERY_SENSOR_OPTION="--no-battery-sensors"
    fi

    # create program services based on the services present in the './services' folder
    echo "creating '$LIB_DIR/systemd/system'"
    mkdir -p "$LIB_DIR/systemd/system"
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        if [ "$SHOULD_PRE_UNINSTALL" = true ] && [ "$(systemctl is-active "$SERVICE")" == "active" ]; then
            echo "stopping [$SERVICE]"
            systemctl stop "$SERVICE"
        fi
        echo "creating '$LIB_DIR/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%BIN_DIR%/${BIN_DIR//\//\\/}/" | sed -e "s/%ETC_DIR%/${ETC_DIR//\//\\/}/" | sed -e "s/%NO_BATTERY_SENSOR_OPTION%/${NO_BATTERY_SENSOR_OPTION}/" | tee "$LIB_DIR/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
    done

    # add program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "adding services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "adding sub-configurations for [$SERVICE]"
        SUBCONFIG_FOLDERS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)"
        # ensure folders exists
        mkdir -p "$LIB_DIR/systemd/$SERVICE"
        for SUBCONFIG_FOLDER in $SUBCONFIG_FOLDERS ; do
            SUBCONFIG_FOLDER=$(sanitizePath "$SUBCONFIG_FOLDER")
            echo "creating '$LIB_DIR/systemd/$SERVICE/$SUBCONFIG_FOLDER'"
            mkdir -p "$LIB_DIR/systemd/$SERVICE/$SUBCONFIG_FOLDER"
        done
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        # add sub-configurations
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "adding '$LIB_DIR/systemd/$SERVICE/$SUBCONFIG'"
            cat "$SERVICES_DIR/$SERVICE/$SUBCONFIG" | sed -e "s/%PREFIX_DIRECTORY%/${PREFIX_DIR//\//\\/}/" | tee "$LIB_DIR/systemd/$SERVICE/$SUBCONFIG" > "/dev/null"
            chmod +x "$LIB_DIR/systemd/$SERVICE/$SUBCONFIG"
        done
    done

    if [ "$SHOULD_POST_INSTALL" = true ]; then
        ./post-install.sh --dest-dir "$DEST_DIR" --sysconf-dir "$SYSCONF_DIR" "$([ "$NO_SUDO" = true ] && echo "--no-sudo")"
    fi

}

function installEctool() {
    workingDirectory=$1
    echo "installing ectool"

    ectoolDestPath="$BIN_DIR/ectool"

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

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0
