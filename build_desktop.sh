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
#
# Note: if you run the built program on a machine with no working sound output
# (some virtual machines), start it with SDL_AUDIODRIVER=dummy to skip audio,
# for example:  SDL_AUDIODRIVER=dummy ./dist/CoinTex

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

# Headless environments (CI runners, servers) can't open the GL window that Kivy
# briefly creates while PyInstaller analyses the app, which aborts the build.
# Handle it here so the same command works with a display and without one:
#   - Linux with no display: run PyInstaller under xvfb when it is available.
#   - Windows software/CI GL is GDI Generic 1.1; the ANGLE backend (bundled in
#     the Windows Kivy wheel) gives GL ES 2.0 via DirectX. Harmless on a real
#     GPU, and only affects this build-time import, not the packaged app.
PYI_PREFIX=""
if [[ "$OS" == "linux" && -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    if command -v xvfb-run >/dev/null 2>&1; then
        echo "No display detected; running PyInstaller under xvfb."
        PYI_PREFIX="xvfb-run -a"
    else
        echo "Warning: no display and xvfb-run not found; the Kivy import may fail." >&2
    fi
fi
if [[ "$OS" == "windows" ]]; then
    export KIVY_GL_BACKEND="${KIVY_GL_BACKEND:-angle_sdl2}"
fi

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

# The game draws everything in code, so the only data to bundle are the music
# and sound files in music/ and the CoinTex logo used for the window and exe
# icons. PyInstaller finds the Python modules on its own, and Kivy ships its own
# PyInstaller hooks so its providers are included. --icon makes Windows show the
# CoinTex logo on the .exe in File Explorer and in the title bar (PyInstaller
# converts the .png to .ico through Pillow, which Kivy already installs).
echo "Running PyInstaller ($MODE)"
$PYI_PREFIX "$PY" -m PyInstaller \
    --noconfirm --clean $MODE --windowed \
    --name CoinTex \
    --icon cointex_logo.png \
    --add-data "music${SEP}music" \
    --add-data "cointex_logo.png${SEP}." \
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
