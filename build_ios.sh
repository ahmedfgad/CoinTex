#!/usr/bin/env bash
#
# Builds the CoinTex iOS app with kivy-ios.
#
# iOS apps can only be built on a Mac with Xcode. This script stops if it is run
# anywhere else. It cannot run on Linux.
#
# What it does on a Mac:
#   1. Checks for Xcode command line tools and Homebrew.
#   2. Installs the packages kivy-ios needs (autoconf, automake, libtool, pkg-config).
#   3. Creates a Python venv and installs kivy-ios and Cython.
#   4. Builds the iOS toolchain (python3 and kivy).
#   5. Creates an Xcode project from this app.
#   6. Prints the steps left to do in Xcode.
#
# Run it on a Mac with:
#   ./build_ios.sh
#
set -euo pipefail
cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"
PROJECT_DIR="$(pwd)"

APP_TITLE="CoinTex"
BUNDLE_ID="coin.tex.cointexreactfast"   # change this if you want a different App Store id
IOS_VENV=".ios-venv"

# Stop if this is not a Mac.
if [[ "$(uname)" != "Darwin" ]]; then
    echo "iOS builds need macOS and Xcode." >&2
    echo "This machine is $(uname), so the build cannot run here." >&2
    echo "Copy the project to a Mac and run this script there. You also need:" >&2
    echo "  - An Apple Developer account to sign and publish the app." >&2
    echo "  - Xcode from the Mac App Store, with its command line tools." >&2
    exit 1
fi

# Check Xcode command line tools.
if ! xcode-select -p >/dev/null 2>&1; then
    echo "Installing Xcode command line tools (a window may open)."
    xcode-select --install || true
    echo "Run this script again after the install finishes." >&2
    exit 1
fi

# Check Homebrew.
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required. Install it from https://brew.sh and run this again." >&2
    exit 1
fi

echo "Installing build packages with Homebrew"
brew install autoconf automake libtool pkg-config

# Create the venv and install kivy-ios.
if [[ ! -d "$IOS_VENV" ]]; then
    echo "Creating iOS build venv ($IOS_VENV)"
    python3 -m venv "$IOS_VENV"
fi
# shellcheck disable=SC1091
source "$IOS_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install --upgrade kivy-ios cython

# Build the toolchain. This is the long step.
echo "Building the iOS toolchain (python3 and kivy)"
toolchain build python3 kivy

# Create the Xcode project.
echo "Creating the Xcode project ${APP_TITLE}-ios/"
rm -rf "${APP_TITLE}-ios"
toolchain create "$APP_TITLE" "$PROJECT_DIR"

# Replace the kivy-ios template's Kivy-logo icon and launch screen with the
# CoinTex artwork. Without this, the installed app shows the Kivy logo on the
# home screen and again as the splash screen.
echo "Applying the CoinTex icon and presplash"
"$PROJECT_DIR/tools/ios_apply_assets.sh" \
    "${APP_TITLE}-ios" cointex_logo.png cointex_presplash.png

echo ""
echo "Xcode project created: ${APP_TITLE}-ios/"
echo ""
echo "Next steps in Xcode:"
echo "  1. open ${APP_TITLE}-ios/${APP_TITLE}.xcodeproj"
echo "  2. In Signing and Capabilities set your team and the bundle id ${BUNDLE_ID}."
echo "  3. Set the deployment target to a recent iOS version."
echo "  4. Choose Any iOS Device and run Product > Archive."
echo "  5. In the Organizer choose Distribute App and upload to App Store Connect."
echo ""
echo "Note: iOS signing uses Apple certificates and is separate from the Android"
echo "keystore. The lost Android key does not affect the iOS build."
