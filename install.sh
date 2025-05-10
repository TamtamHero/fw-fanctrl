#!/bin/bash
set -e

# Argument parsing
SHORT=r,d:,p:,s:,h
LONG=remove,dest-dir:,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-post-install,no-battery-sensors,no-sudo,no-pip-install,pipx,python-prefix-dir:,effective-installation-dir:,help
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
NO_PIP_INSTALL=false
PIPX=false
PYTHON_PREFIX_DIRECTORY_OVERRIDE=
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
    '--python-prefix-dir')
        PYTHON_PREFIX_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--effective-installation-dir')
        EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE=$2
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--dest-dir,-d <installation destination directory (defaults to $DEST_DIR)>] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s system configuration destination directory (defaults to $SYSCONF_DIR)] [--no-ectool] [--no-post-install] [--no-pre-uninstall] [--no-sudo] [--no-pip-install] [--pipx] [--python-prefix-dir (defaults to $DEST_DIR$PREFIX_DIR)]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done

PYTHON_PREFIX_DIRECTORY="$DEST_DIR$PREFIX_DIR"
if [ -n "$PYTHON_PREFIX_DIRECTORY_OVERRIDE" ]; then
    PYTHON_PREFIX_DIRECTORY=$PYTHON_PREFIX_DIRECTORY_OVERRIDE
fi

INSTALLATION_DIRECTORY="$PYTHON_PREFIX_DIRECTORY/bin"
if [ -n "$EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE" ]; then
    INSTALLATION_DIRECTORY=$EFFECTIVE_INSTALLATION_DIRECTORY_OVERRIDE
fi

PYTHON_SCRIPT_INSTALLATION_PATH="$INSTALLATION_DIRECTORY/fw-fanctrl"

if ! python3 -h 1>/dev/null 2>&1; then
    echo "Missing package 'python3'!"
    exit 1
fi

if [ "$NO_PIP_INSTALL" = false ]; then
    if ! python3 -m pip -h 1>/dev/null 2>&1; then
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
    if ! python3 -m build -h 1>/dev/null 2>&1; then
        echo "Missing python package 'build'!"
        exit 1
    fi
fi

# Root check
if [ "$EUID" -ne 0 ] && [ "$NO_SUDO" = false ]
  then echo "This program requires root permissions or use the '--no-sudo' option"
  exit 1
fi

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

function build() {
    echo "building package"
    remove_target "dist/"
    python3 -m build -s
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

# remove remaining legacy files
function uninstall_legacy() {
    echo "removing legacy files"
    remove_target "/usr/local/bin/fw-fanctrl"
    remove_target "/usr/local/bin/ectool"
    remove_target "/usr/local/bin/fanctrl.py"
    remove_target "/etc/systemd/system/fw-fanctrl.service"
    remove_target "$DEST_DIR$PREFIX_DIR/bin/fw-fanctrl"
}

function uninstall() {
    if [ "$SHOULD_PRE_UNINSTALL" = true ]; then
        if ! ./pre-uninstall.sh "$([ "$NO_SUDO" = true ] && echo "--no-sudo")"; then
            echo "Failed to run ./pre-uninstall.sh. Run the script with root permissions,"
            echo "or skip this step by using the --no-pre-uninstall option."
            exit 1
        fi
    fi
    # remove program services based on the services present in the './services' folder
    echo "removing services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        # be EXTRA CAREFUL about the validity of the paths (dont wanna delete something important, right?... O_O)
        remove_target "$DEST_DIR$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION"
    done

    # remove program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "removing services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "removing sub-configurations for [$SERVICE]"
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "removing '$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG'"
            remove_target "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG"
        done
    done

    if [ "$NO_PIP_INSTALL" = false ]; then
        echo "uninstalling python package"
        if [ "$PIPX" = false ]; then
            python3 -m pip uninstall -y fw-fanctrl 2> "/dev/null" || true
        else
            pipx --global uinistall fw-fanctrl 2> "/dev/null" || true
        fi
    fi

    ectool autofanctrl 2> "/dev/null" || true # restore default fan manager
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        remove_target "$DEST_DIR$PREFIX_DIR/bin/ectool"
    fi
    remove_target "$DEST_DIR$SYSCONF_DIR/fw-fanctrl"
    remove_target "/run/fw-fanctrl"

    uninstall_legacy
}

function install() {
    uninstall_legacy

    remove_target "$TEMP_FOLDER"
    mkdir -p "$DEST_DIR$PREFIX_DIR/bin"
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        mkdir "$TEMP_FOLDER"
        installEctool "$TEMP_FOLDER" || (echo "an error occurred when installing ectool." && echo "please check your internet connection or consider installing it manually and using --no-ectool on the installation script." && exit 1)
        remove_target "$TEMP_FOLDER"
    fi
    mkdir -p "$DEST_DIR$SYSCONF_DIR/fw-fanctrl"

    build

    if [ "$NO_PIP_INSTALL" = false ]; then
        echo "installing python package"
        if [ "$PIPX" = false ]; then
            python3 -m pip install --prefix="$PYTHON_PREFIX_DIRECTORY" dist/*.tar.gz
            which python3
        else
            pipx install --global --force dist/*.tar.gz
        fi
        which 'fw-fanctrl' 2> "/dev/null" || true
        remove_target "dist/"
    fi

    cp -pn "./src/fw_fanctrl/_resources/config.json" "$DEST_DIR$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true
    cp -f "./src/fw_fanctrl/_resources/config.schema.json" "$DEST_DIR$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true

    # add --no-battery-sensors flag to the fanctrl service if specified
    if [ "$NO_BATTERY_SENSOR" = true ]; then
        NO_BATTERY_SENSOR_OPTION="--no-battery-sensors"
    fi

    # create program services based on the services present in the './services' folder
    echo "creating '$DEST_DIR$PREFIX_DIR/lib/systemd/system'"
    mkdir -p "$DEST_DIR$PREFIX_DIR/lib/systemd/system"
    echo "creating services"
    for SERVICE in $SERVICES ; do
        SERVICE=$(sanitizePath "$SERVICE")
        if [ "$SHOULD_PRE_UNINSTALL" = true ] && [ "$(systemctl is-active "$SERVICE")" == "active" ]; then
            echo "stopping [$SERVICE]"
            systemctl stop "$SERVICE"
        fi
        echo "creating '$DEST_DIR$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION'"
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%PYTHON_SCRIPT_INSTALLATION_PATH%/${PYTHON_SCRIPT_INSTALLATION_PATH//\//\\/}/" | sed -e "s/%SYSCONF_DIRECTORY%/${SYSCONF_DIR//\//\\/}/" | sed -e "s/%NO_BATTERY_SENSOR_OPTION%/${NO_BATTERY_SENSOR_OPTION}/" | tee "$DEST_DIR$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
    done

    # add program services sub-configurations based on the sub-configurations present in the './services' folder
    echo "adding services sub-configurations"
    for SERVICE in $SERVICES_SUBCONFIGS ; do
        SERVICE=$(sanitizePath "$SERVICE")
        echo "adding sub-configurations for [$SERVICE]"
        SUBCONFIG_FOLDERS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)"
        # ensure folders exists
        mkdir -p "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE"
        for SUBCONFIG_FOLDER in $SUBCONFIG_FOLDERS ; do
            SUBCONFIG_FOLDER=$(sanitizePath "$SUBCONFIG_FOLDER")
            echo "creating '$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG_FOLDER'"
            mkdir -p "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG_FOLDER"
        done
        SUBCONFIGS="$(cd "$SERVICES_DIR/$SERVICE" && find . -mindepth 1 -type f)"
        # add sub-configurations
        for SUBCONFIG in $SUBCONFIGS ; do
            SUBCONFIG=$(sanitizePath "$SUBCONFIG")
            echo "adding '$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG'"
            cat "$SERVICES_DIR/$SERVICE/$SUBCONFIG" | sed -e "s/%PYTHON_SCRIPT_INSTALLATION_PATH%/${PYTHON_SCRIPT_INSTALLATION_PATH//\//\\/}/" | tee "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG" > "/dev/null"
            chmod +x "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG"
        done
    done
    if [ "$SHOULD_POST_INSTALL" = true ]; then
        if ! ./post-install.sh --dest-dir "$DEST_DIR" --sysconf-dir "$SYSCONF_DIR" "$([ "$NO_SUDO" = true ] && echo "--no-sudo")"; then
            echo "Failed to run ./post-install.sh. Run the script with root permissions,"
            echo "or skip this step by using the --no-post-install option."
            exit 1
        fi
    fi
}

function installEctool() {
    workingDirectory=$1
    echo "installing ectool"

    ectoolDestPath="$DEST_DIR$PREFIX_DIR/bin/ectool"

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
