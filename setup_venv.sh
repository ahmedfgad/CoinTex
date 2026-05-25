#!/usr/bin/env bash
#
# Sets up everything needed to run and build CoinTex.
#
# It does four things:
#   1. Creates a Python 3.12 virtual environment in ./venv and installs Kivy.
#   2. Installs the Linux libraries Kivy needs to run (SDL2, OpenGL, xvfb).
#   3. Installs the Android build tools (JDK 17, autotools, cmake and so on).
#   4. Installs buildozer and Cython in the venv.
#
# Steps 2-4 use apt and ask for your sudo password.
#
# Options:
#   ./setup_venv.sh                     full setup
#   ./setup_venv.sh --dev               also install pygad and numpy (PlayerGA)
#   ./setup_venv.sh --no-android        skip the Android build tools
#   ./setup_venv.sh --skip-system-deps  only create the venv, no apt, no sudo
#
set -euo pipefail

# Work from the folder this script is in.
cd "$(dirname "$(readlink -f "$0")")"

VENV_DIR="venv"
REQ_FILE="requirements.txt"
SKIP_SYSTEM_DEPS=0
INSTALL_ANDROID=1
for arg in "$@"; do
    case "$arg" in
        --dev)              REQ_FILE="requirements-dev.txt" ;;
        --no-android)       INSTALL_ANDROID=0 ;;
        --skip-system-deps) SKIP_SYSTEM_DEPS=1 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# Find a Python 3.12 interpreter.
find_python312() {
    for candidate in python3.12 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' 2>/dev/null; then
                command -v "$candidate"; return 0
            fi
        fi
    done
    return 1
}

PYTHON="$(find_python312 || true)"
if [[ -z "$PYTHON" ]]; then
    echo "Python 3.12 was not found." >&2
    echo "On Debian/Ubuntu install it with:" >&2
    echo "    sudo apt update && sudo apt install -y python3.12 python3.12-venv" >&2
    exit 1
fi
echo "Using $PYTHON ($("$PYTHON" --version 2>&1))"

# Create the virtual environment.
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in ./$VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
else
    echo "Using existing virtual environment ./$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Install the Python packages.
echo "Upgrading pip, setuptools and wheel"
python -m pip install --upgrade pip setuptools wheel
echo "Installing packages from $REQ_FILE"
python -m pip install -r "$REQ_FILE"

# Libraries Kivy needs to run on Linux. They are not part of the pip wheels on
# Linux, so they come from apt. xvfb lets the game run without a screen.
DESKTOP_PKGS="xvfb libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 \
libsdl2-ttf-2.0-0 libglew2.2 libgl1-mesa-dri libgles2 libmtdev1"

# Tools buildozer needs to build the Android package. zlib1g-dev is handled
# below because of a version problem on Ubuntu.
ANDROID_PKGS="git zip unzip openjdk-17-jdk autoconf automake libtool pkg-config \
libncurses-dev cmake libffi-dev libssl-dev build-essential ccache"

if [[ "$SKIP_SYSTEM_DEPS" -eq 1 ]]; then
    echo "Skipping system packages (--skip-system-deps)."
elif ! command -v apt-get >/dev/null 2>&1; then
    echo "This is not an apt system. Install these packages for your distro:"
    echo "    desktop: $DESKTOP_PKGS"
    [[ "$INSTALL_ANDROID" -eq 1 ]] && echo "    android: $ANDROID_PKGS zlib1g-dev"
else
    PKGS="$DESKTOP_PKGS"
    ZLIB_ARGS=()
    if [[ "$INSTALL_ANDROID" -eq 1 ]]; then
        PKGS="$PKGS $ANDROID_PKGS"
        # zlib1g-dev asks for the exact zlib1g version it was built with. After a
        # security update the installed zlib1g can be newer than the zlib1g-dev in
        # the repo, and the install fails. Pin both to the zlib1g-dev version so
        # they match (this can downgrade zlib1g by one patch level).
        zdev="$(apt-cache policy zlib1g-dev 2>/dev/null | awk '/Candidate:/{print $2}')"
        if [[ -n "$zdev" && "$zdev" != "(none)" ]]; then
            ZLIB_ARGS=(--allow-downgrades "zlib1g=$zdev" "zlib1g-dev=$zdev")
        else
            PKGS="$PKGS zlib1g-dev"
        fi
    fi

    echo "Installing system packages with sudo:"
    echo "    $PKGS ${ZLIB_ARGS[*]}"
    sudo apt-get update
    # shellcheck disable=SC2086
    sudo apt-get install -y $PKGS "${ZLIB_ARGS[@]}"

    if [[ "$INSTALL_ANDROID" -eq 1 ]]; then
        echo "Installing buildozer and Cython in the venv"
        python -m pip install --upgrade buildozer cython
    fi
fi

# Print a short summary.
SDL_OK="missing"; ldconfig -p 2>/dev/null | grep -qi "libSDL2-2.0.so.0" && SDL_OK="ok"
JDK_OK="missing"; command -v javac >/dev/null 2>&1 && JDK_OK="ok ($(javac -version 2>&1))"
echo ""
echo "Done."
echo "  Python venv:    ./$VENV_DIR ($(python --version 2>&1))"
echo "  Kivy:           $(python -c 'import kivy; print(kivy.__version__)' 2>/dev/null || echo '??')"
echo "  SDL2 libraries: $SDL_OK"
[[ "$INSTALL_ANDROID" -eq 1 ]] && echo "  Android JDK:    $JDK_OK"
echo ""
echo "Activate the venv:   source $VENV_DIR/bin/activate"
echo "Run the game:        python main.py"
echo "Run without screen:  xvfb-run -a python main.py"
[[ "$INSTALL_ANDROID" -eq 1 ]] && echo "Build for Android:   ./build_android.sh"
