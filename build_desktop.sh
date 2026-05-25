#!/usr/bin/env bash
#
# Builds CoinTex as a standalone desktop program with PyInstaller.
#
# PyInstaller builds for the system it runs on. It cannot build a Windows file
# from Linux or the other way round, so run this on each system you want:
#   - On Linux it makes a Linux executable.
#   - On Windows run it inside Git Bash or MSYS2; it makes a Windows .exe.
#   - On macOS it makes a macOS .app.
#
# Options:
#   ./build_desktop.sh            one standalone file (default)
#   ./build_desktop.sh --onedir   a folder with the executable next to its files
#                                  (starts faster and is easy to zip and share)
#
# The result is written to the dist/ folder.

set -euo pipefail
cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"

ONEFILE=1
for arg in "$@"; do
    case "$arg" in
        --onedir)  ONEFILE=0 ;;
        --onefile) ONEFILE=1 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# Work out the system, the matching venv layout and the data separator.
# PyInstaller wants ":" between a data source and its target on Linux and macOS,
# and ";" on Windows.
case "$(uname -s)" in
    Linux*)               OS="linux";   VENV_BIN="venv/bin";     SEP=":" ;;
    Darwin*)              OS="macos";   VENV_BIN="venv/bin";     SEP=":" ;;
    MINGW*|MSYS*|CYGWIN*) OS="windows"; VENV_BIN="venv/Scripts"; SEP=";" ;;
    *) echo "Unsupported system: $(uname -s)" >&2; exit 1 ;;
esac
echo "Building CoinTex for $OS"

# Create the venv the first time, then make sure Kivy and PyInstaller are in it.
if [[ ! -d "venv" ]]; then
    echo "Creating a virtual environment in ./venv"
    python3 -m venv venv 2>/dev/null || python -m venv venv
fi
PY="$VENV_BIN/python"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt
"$PY" -m pip install --upgrade pyinstaller

# Start each build clean.
rm -rf build dist CoinTex.spec

MODE="--onefile"
[[ "$ONEFILE" -eq 0 ]] && MODE="--onedir"

# The game draws everything in code, so the only data to bundle is the music and
# sound files in music/. PyInstaller finds the Python modules on its own, and
# Kivy ships its own PyInstaller hooks so its providers are included.
echo "Running PyInstaller ($MODE)"
"$PY" -m PyInstaller \
    --noconfirm --clean $MODE --windowed \
    --name CoinTex \
    --add-data "music${SEP}music" \
    main.py

echo ""
echo "Build finished. Output in ./dist:"
ls -1 dist/ 2>/dev/null || true
echo ""
if [[ "$ONEFILE" -eq 1 ]]; then
    case "$OS" in
        linux)   echo "Run it with:  ./dist/CoinTex   (a single file you can copy to another Linux PC)" ;;
        macos)   echo "Open dist/CoinTex.app, or run ./dist/CoinTex from a terminal." ;;
        windows) echo "Run dist\\CoinTex.exe   (a single file you can copy to another Windows PC)" ;;
    esac
    echo "The first start takes a few seconds while the single file unpacks itself."
else
    case "$OS" in
        windows) echo "Share the whole dist\\CoinTex folder; run CoinTex.exe inside it." ;;
        *)       echo "Share the whole dist/CoinTex folder; run CoinTex inside it." ;;
    esac
fi
