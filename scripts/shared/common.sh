#!/bin/bash

# safe remove function
function remove_target() {
    local target="$1"
    if [ -e "$target" ] || [ -L "$target" ]; then
        if ! rm -rf "$target" 2> "/dev/null"; then
            echo "Failed to remove: $target"
            exit 1
        fi
    fi
}

function sanitizePath() {
    local SANITIZED_PATH="$1"
    local SANITIZED_PATH=${SANITIZED_PATH//..\//}
    local SANITIZED_PATH=${SANITIZED_PATH#./}
    local SANITIZED_PATH=${SANITIZED_PATH#/}
    echo "$SANITIZED_PATH"
}

function contains() {
  local needle="$1"
  shift
  local x
  for x in "$@"; do
    [ "$x" = "$needle" ] && return 0
  done
  return 1
}

# remove remaining legacy files
function uninstall_legacy() {
    echo "removing legacy files"
    reset_tool "ectool" "$PREFIX_DIR/bin"
    reset_tool "ectool" "/usr/local/bin"
    if ! contains "ectool" "${IGNORED_TOOLS[@]}"; then
        uninstall_tool "ectool" "$PREFIX_DIR/bin"
        uninstall_tool "ectool" "/usr/local/bin"
    fi
    python3 -m pip uninstall -y fw-fanctrl 2> "/dev/null" || true
    pipx --global uinistall fw-fanctrl 2> "/dev/null" || true
    remove_target "/usr/local/bin/fw-fanctrl"
    remove_target "/usr/local/bin/fanctrl.py"
    remove_target "/etc/systemd/system/fw-fanctrl.service"
    remove_target "$PREFIX_DIR/bin/fw-fanctrl"
}

function reset_tool() {
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

function uninstall_tool() {
    toolId="$1"
    toolPath="$2/$toolId"

    echo "Uninstalling $toolId"
    reset_tool "$1" "$2"

    remove_target "$toolPath"
    echo "$toolId uninstalled from '$toolPath'"
}
