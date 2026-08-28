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
#   3. Verifies Xcode/iOS SDK 26 (required for current App Store uploads).
#   4. Creates a Python venv and installs the pinned iOS toolchain.
#   5. Builds Python/Kivy and installs the verified CA bundle.
#   6. Creates and configures an App Store-ready Xcode project.
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
IOS_STAGE=".ios-app"
IOS_PROJECT="cointex-ios"

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

XCODE_MAJOR=$(xcodebuild -version | awk '/^Xcode / {split($2, v, "."); print v[1]}')
SDK_MAJOR=$(xcrun --sdk iphoneos --show-sdk-version | awk -F. '{print $1}')
if [[ -z "$XCODE_MAJOR" || "$XCODE_MAJOR" -lt 26 || \
      -z "$SDK_MAJOR" || "$SDK_MAJOR" -lt 26 ]]; then
    echo "App Store uploads now require Xcode 26 and the iOS 26 SDK." >&2
    echo "Found: $(xcodebuild -version | head -1), iOS SDK $(xcrun --sdk iphoneos --show-sdk-version)" >&2
    exit 1
fi
echo "Using $(xcodebuild -version | head -1), iOS SDK $(xcrun --sdk iphoneos --show-sdk-version)"

# Check Homebrew.
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required. Install it from https://brew.sh and run this again." >&2
    exit 1
fi

echo "Installing build packages with Homebrew"
brew install autoconf automake libtool pkg-config libjpeg
brew link libtool || true

# Create the venv and install kivy-ios.
if [[ ! -d "$IOS_VENV" ]]; then
    echo "Creating iOS build venv ($IOS_VENV)"
    python3 -m venv "$IOS_VENV"
fi
# shellcheck disable=SC1091
source "$IOS_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-ios.txt

# Build the toolchain. This is the long step.
echo "Building the iOS toolchain (python3 and kivy)"
toolchain build python3 kivy
CERTIFI_REQUIREMENT=$(awk '/^certifi==/ {print; exit}' requirements-ios.txt)
if [[ -z "$CERTIFI_REQUIREMENT" ]]; then
    echo "certifi pin is missing from requirements-ios.txt" >&2
    exit 1
fi
toolchain pip install "$CERTIFI_REQUIREMENT"

# Package only runtime files. Pointing kivy-ios at the repository root would
# copy development media, documentation and potentially local secrets into the
# app bundle on every Xcode build.
echo "Staging runtime files"
rm -rf "$IOS_STAGE"
mkdir -p "$IOS_STAGE/music"
cp ./*.py "$IOS_STAGE/"
cp music/*.wav "$IOS_STAGE/music/"

# Create the Xcode project.
echo "Creating the Xcode project ${IOS_PROJECT}/"
rm -rf "$IOS_PROJECT"
toolchain create "$APP_TITLE" "$IOS_STAGE"

echo "Applying App Store metadata and privacy declarations"
python tools/ios_configure_project.py "$IOS_PROJECT" --app-source "$IOS_STAGE"

# Replace the kivy-ios template's Kivy-logo icon and launch screen with the
# CoinTex artwork. Without this, the installed app shows the Kivy logo on the
# home screen and again as the splash screen.
echo "Applying the CoinTex icon and presplash"
"$PROJECT_DIR/tools/ios_apply_assets.sh" \
    "$IOS_PROJECT" cointex_logo.png cointex_presplash.png

echo ""
echo "Xcode project created: ${IOS_PROJECT}/"
echo ""
echo "Next steps in Xcode:"
echo "  1. open ${IOS_PROJECT}/cointex.xcodeproj"
echo "  2. In Signing & Capabilities select your Apple Developer team."
echo "     The configured bundle id is ${BUNDLE_ID}."
echo "  3. Run on a real iPhone and then distribute through TestFlight."
echo "  4. Choose Any iOS Device and run Product > Archive."
echo "  5. In Organizer choose Distribute App > App Store Connect."
echo ""
echo "Note: iOS signing uses Apple certificates and is separate from the Android"
echo "keystore. The lost Android key does not affect the iOS build."
