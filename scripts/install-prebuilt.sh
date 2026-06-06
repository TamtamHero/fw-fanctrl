#!/bin/sh
set -eu

REPOSITORY="TamtamHero/fw-fanctrl"
BASE_URL="https://github.com/$REPOSITORY"
API_URL="https://api.github.com/repos/$REPOSITORY/releases/latest"

case "$(uname -s)" in
    Linux)
        ARTIFACT_SYSTEM="linux"
        ;;
    *)
        echo "Unsupported operating system: $(uname -s)" >&2
        exit 1
        ;;
esac

case "$(uname -m)" in
    x86_64|amd64)
        ARTIFACT_ARCH="x86_64"
        ;;
    *)
        echo "Unsupported architecture: $(uname -m)" >&2
        exit 1
        ;;
esac

for COMMAND in curl tar mktemp; do
    if ! command -v "$COMMAND" >/dev/null 2>&1; then
        echo "Missing required command: $COMMAND" >&2
        exit 1
    fi
done

if [ -n "${FW_FANCTRL_VERSION:-}" ]; then
    TAG="v${FW_FANCTRL_VERSION#v}"
else
    TAG="$(curl -fsSL "$API_URL" | sed -n '/"tag_name"/ { s/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p; q; }')"
fi

if [ -z "$TAG" ]; then
    echo "Failed to resolve latest fw-fanctrl release" >&2
    exit 1
fi

VERSION="${TAG#v}"
ASSET="fw-fanctrl-v$VERSION-$ARTIFACT_SYSTEM-$ARTIFACT_ARCH"
ASSET_URL="$BASE_URL/releases/download/$TAG/$ASSET"
SOURCE_ARCHIVE_URL="$BASE_URL/archive/refs/tags/$TAG.tar.gz"
TEMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT INT TERM

echo "Downloading fw-fanctrl $TAG source archive"
curl -fsSL "$SOURCE_ARCHIVE_URL" -o "$TEMP_DIR/source.tar.gz"
tar -xzf "$TEMP_DIR/source.tar.gz" -C "$TEMP_DIR"

SOURCE_DIR=""
for DIRECTORY in "$TEMP_DIR"/fw-fanctrl-*; do
    if [ -d "$DIRECTORY" ]; then
        SOURCE_DIR="$DIRECTORY"
        break
    fi
done

if [ -z "$SOURCE_DIR" ]; then
    echo "Failed to locate extracted fw-fanctrl source archive" >&2
    exit 1
fi

echo "Downloading fw-fanctrl $TAG prebuilt executable for $ARTIFACT_SYSTEM-$ARTIFACT_ARCH"
mkdir -p "$SOURCE_DIR/build/nuitka"
curl -fsSL "$ASSET_URL" -o "$SOURCE_DIR/build/nuitka/fw-fanctrl"

cd "$SOURCE_DIR"
chmod +x ./install.sh ./build/nuitka/fw-fanctrl

exec ./install.sh --no-build "$@"
