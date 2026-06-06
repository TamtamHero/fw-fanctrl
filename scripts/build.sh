#!/bin/bash
set -e
source ./scripts/shared/common.sh

IS_MANUAL_ENV=false

SHORT=,
LONG=manual-env,help
VALID_ARGS=$(getopt -a --options $SHORT --longoptions $LONG -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

eval set -- "$VALID_ARGS"
while true; do
  case "$1" in
    '--manual-env')
        IS_MANUAL_ENV=true
        ;;
    '--help' | '-h')
        echo "Usage: $0 [--manual-env]" 1>&2
        exit 0
        ;;
    --)
        break
        ;;
  esac
  shift
done

function check_requirements() {
    if ! python3 -h 1>/dev/null 2>&1; then
        echo "Missing package 'python3'!"
        exit 1
    fi

    if [ "$IS_MANUAL_ENV" = false ]; then
        if ! python3 -m venv -h 1>/dev/null 2>&1; then
            echo "Missing python package 'venv'!"
            exit 1
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
}

function initialize_env() {
    echo "Initializing virtual environment"
    python3 -m venv .venv
    echo "Activating virtual environment"
    source .venv/bin/activate
    echo "Installing runtime and compilation dependencies"
    python3 -m pip install -e ".[compile]"
}

function build() {
    check_requirements

    if [ "$IS_MANUAL_ENV" = false ]; then
        initialize_env
    fi

    echo "building package"
    remove_target "dist/"
    python3 -m nuitka --onefile --follow-imports --include-package=fw_fanctrl --include-package-data=fw_fanctrl --output-dir=build/nuitka --output-filename=fw-fanctrl "main.py"
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2> "/dev/null" || true
}

build
