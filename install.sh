#!/bin/bash
set -e


# Argument parsing
SHORT=r,d:,p:,s:,h
LONG=remove,dest-dir:,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-post-install,no-sudo,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

PREFIX_DIR="/usr"
DEST_DIR=""
SYSCONF_DIR="/etc"
SHOULD_INSTALL_ECTOOL=true
SHOULD_PRE_UNINSTALL=true
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false
NO_SUDO=false

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
    '--no-sudo')
        NO_SUDO=true
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
  then echo "This program requires root permissions"
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
        rm -rf "$DEST_DIR$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION"
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
            rm -rf "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG" 2> "/dev/null" || true
        done
    done

    rm "$DEST_DIR$PREFIX_DIR/bin/fw-fanctrl" 2> "/dev/null" || true
    ectool autofanctrl 2> "/dev/null" || true # restore default fan manager
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        rm "$DEST_DIR$PREFIX_DIR/bin/ectool" 2> "/dev/null" || true
    fi
    rm -rf "$DEST_DIR$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true
    rm -rf "/run/fw-fanctrl" 2> "/dev/null" || true

    uninstall_legacy
}

function install() {
    uninstall_legacy

    mkdir -p "$DEST_DIR$PREFIX_DIR/bin"
    if [ "$SHOULD_INSTALL_ECTOOL" = true ]; then
        cp "./bin/ectool" "$DEST_DIR$PREFIX_DIR/bin/ectool"
        chmod +x "$DEST_DIR$PREFIX_DIR/bin/ectool"
    fi
    mkdir -p "$DEST_DIR$SYSCONF_DIR/fw-fanctrl"
    cp "./fanctrl.py" "$DEST_DIR$PREFIX_DIR/bin/fw-fanctrl"
    chmod +x "$DEST_DIR$PREFIX_DIR/bin/fw-fanctrl"

    cp -n "./config.json" "$DEST_DIR$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true

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
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%PREFIX_DIRECTORY%/${PREFIX_DIR//\//\\/}/" | sed -e "s/%SYSCONF_DIRECTORY%/${SYSCONF_DIR//\//\\/}/" | tee "$DEST_DIR$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
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
            cat "$SERVICES_DIR/$SERVICE/$SUBCONFIG" | sed -e "s/%PREFIX_DIRECTORY%/${PREFIX_DIR//\//\\/}/" | tee "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG" > "/dev/null"
            chmod +x "$DEST_DIR$PREFIX_DIR/lib/systemd/$SERVICE/$SUBCONFIG"
        done
    done
    if [ "$SHOULD_POST_INSTALL" = true ]; then
      ./post-install.sh --dest-dir "$DEST_DIR" --sysconf-dir "$SYSCONF_DIR" "$([ "$NO_SUDO" = true ] && echo "--no-sudo")"
    fi
}

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0
