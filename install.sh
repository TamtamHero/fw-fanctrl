#!/bin/bash
set -e

# Argument parsing
SHORT=r,d:,p:,s:,h
LONG=remove,dest-dir:,prefix-dir:,sysconf-dir:,no-ectool,no-pre-uninstall,no-post-install,no-sudo,no-pip-install,pipx,python-prefix-dir:,effective-installation-dir:,ignore-tool:,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

TEMP_FOLDER='./.temp'
trap 'rm -rf $TEMP_FOLDER' EXIT

PREFIX_DIR="/usr"
DEST_DIR=""
SYSCONF_DIR="/etc"
IGNORED_TOOLS=()
SHOULD_PRE_UNINSTALL=true
SHOULD_POST_INSTALL=true
SHOULD_REMOVE=false
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
        # legacy
        IGNORED_TOOLS+=("ectool")
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
    '--ignore-tool')
        IGNORED_TOOLS+=("$2")
        shift
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--remove,-r] [--dest-dir,-d <installation destination directory (defaults to $DEST_DIR)>] [--prefix-dir,-p <installation prefix directory (defaults to $PREFIX_DIR)>] [--sysconf-dir,-s <system configuration destination directory (defaults to $SYSCONF_DIR)>] [--ignore-tool <tool id to ignore (e.g. 'framework_tool')>] [--no-post-install] [--no-pre-uninstall] [--no-sudo] [--no-pip-install] [--pipx] [--python-prefix-dir <(defaults to $DEST_DIR$PREFIX_DIR)>]" 1>&2
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
    if [ "$PIPX" = true ]; then
        if ! pipx -h >/dev/null 2>&1; then
            echo "Missing package 'pipx'!"
            exit 1
        fi
    else
        if ! python3 -m pip -h 1>/dev/null 2>&1; then
            echo "Missing python package 'pip'!"
            exit 1
        fi
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
    resetTool "ectool" "$DEST_DIR$PREFIX_DIR/bin"
    resetTool "ectool" "/usr/local/bin"
    if ! contains "ectool" "${IGNORED_TOOLS[@]}"; then
        unInstallTool "ectool" "$DEST_DIR$PREFIX_DIR/bin"
        unInstallTool "ectool" "/usr/local/bin"
    fi
    remove_target "/usr/local/bin/fw-fanctrl"
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

    if [ "$NO_PIP_INSTALL" = false ]; then
        echo "uninstalling python package"
        if [ "$PIPX" = false ]; then
            python3 -m pip uninstall -y fw-fanctrl 2> "/dev/null" || true
        else
            pipx --global uninstall fw-fanctrl 2> "/dev/null" || true
        fi
    fi

    resetTool "framework_tool" "$DEST_DIR$PREFIX_DIR/bin"
    if ! contains "framework_tool" "${IGNORED_TOOLS[@]}"; then
        unInstallTool "framework_tool" "$DEST_DIR$PREFIX_DIR/bin"
    fi
    remove_target "$DEST_DIR$SYSCONF_DIR/fw-fanctrl"
    remove_target "/run/fw-fanctrl"

    uninstall_legacy
}

function install() {
    uninstall_legacy

    remove_target "$TEMP_FOLDER"
    mkdir -p "$DEST_DIR$PREFIX_DIR/bin"
    if ! contains "framework_tool" "${IGNORED_TOOLS[@]}"; then
        mkdir "$TEMP_FOLDER"
        installFrameworkTool "$TEMP_FOLDER" || (echo "an error occurred when installing framework_tool." && echo "please check your internet connection or consider installing it manually and using '--ignore-tool framework_tool' on the installation script." && exit 1)
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
            FW_FANCTRL_BIN=""
            PIPX_BIN_DIR="$(pipx environment --value PIPX_BIN_DIR --global 2>/dev/null || true)"
            if [ -n "$PIPX_BIN_DIR" ] && [ -f "$PIPX_BIN_DIR/fw-fanctrl" ]; then
                FW_FANCTRL_BIN="$PIPX_BIN_DIR/fw-fanctrl"
            elif [ -f "$PYTHON_SCRIPT_INSTALLATION_PATH" ]; then
                FW_FANCTRL_BIN="$PYTHON_SCRIPT_INSTALLATION_PATH"
            fi
            if [ -n "$FW_FANCTRL_BIN" ]; then
                SHEBANG_PYTHON="$(head -1 "$FW_FANCTRL_BIN" | sed 's|^#!||')"
                RESOLVED_PYTHON="$(readlink -f "$SHEBANG_PYTHON" 2>/dev/null || echo "$SHEBANG_PYTHON")"
                if [[ "$RESOLVED_PYTHON" == /home/* ]]; then
                    echo ""
                    echo "⚠  WARNING: the pipx venv is using a Python interpreter under /home ($RESOLVED_PYTHON)."
                    echo "   This is likely Homebrew Python. On SELinux-enforcing systems, systemd will be"
                    echo "   unable to execute the service. To fix, create a dedicated venv with the system Python:"
                    echo ""
                    echo "   sudo /usr/bin/python3 -m venv /opt/fw-fanctrl-venv"
                    echo "   sudo /opt/fw-fanctrl-venv/bin/pip install fw-fanctrl"
                    echo "   sudo ln -sf /opt/fw-fanctrl-venv/bin/fw-fanctrl /var/usrlocal/bin/fw-fanctrl"
                    echo "   sudo systemctl restart fw-fanctrl"
                    echo ""
                fi
            fi
        fi
        which 'fw-fanctrl' 2> "/dev/null" || true
        remove_target "dist/"
    fi

    cp -pn "./src/fw_fanctrl/_resources/config.json" "$DEST_DIR$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true
    cp -f "./src/fw_fanctrl/_resources/config.schema.json" "$DEST_DIR$SYSCONF_DIR/fw-fanctrl" 2> "/dev/null" || true

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
        cat "$SERVICES_DIR/$SERVICE$SERVICE_EXTENSION" | sed -e "s/%PYTHON_SCRIPT_INSTALLATION_PATH%/${PYTHON_SCRIPT_INSTALLATION_PATH//\//\\/}/" | sed -e "s/%SYSCONF_DIRECTORY%/${SYSCONF_DIR//\//\\/}/" | tee "$DEST_DIR$PREFIX_DIR/lib/systemd/system/$SERVICE$SERVICE_EXTENSION" > "/dev/null"
    done

    if [ "$SHOULD_POST_INSTALL" = true ]; then
        if ! ./post-install.sh --dest-dir "$DEST_DIR" --sysconf-dir "$SYSCONF_DIR" "$([ "$NO_SUDO" = true ] && echo "--no-sudo")"; then
            echo "Failed to run ./post-install.sh. Run the script with root permissions,"
            echo "or skip this step by using the --no-post-install option."
            exit 1
        fi
    fi
}

function resetTool() {
    toolId="$1"
    toolPath="$2/$toolId"

    echo "Resetting $toolId"

    # legacy
    if [ "$toolId" = "ectool" ]; then
        "$toolPath" autofanctrl 2> "/dev/null" || true
    fi

    if [ "$toolId" = "framework_tool" ]; then
        "$toolPath" --autofanctrl 2> "/dev/null" || true
    fi

    echo "$toolId reset"
}

function unInstallTool() {
    toolId="$1"
    toolPath="$2/$toolId"

    echo "Uninstalling $toolId"
    resetTool "$1" "$2"

    remove_target "$toolPath"
    echo "$toolId uninstalled from '$toolPath'"
}


function installTool() {
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

function installFrameworkTool() {
    installTool "$1" "framework_tool" "$DEST_DIR$PREFIX_DIR/bin"
}

contains() {
  local needle="$1"
  shift
  local x
  for x in "$@"; do
    [ "$x" = "$needle" ] && return 0
  done
  return 1
}

if [ "$SHOULD_REMOVE" = true ]; then
    uninstall
else
    install
fi
exit 0
