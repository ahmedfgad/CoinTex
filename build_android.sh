#!/usr/bin/env bash
#
# Builds the CoinTex Android package, ready to upload to Google Play.
#
# What it does:
#   1. Activates the venv and makes sure buildozer and Cython are installed.
#   2. Checks that the Android build tools are present (installed by setup_venv.sh).
#   3. Creates a release upload key the first time, and exports its certificate.
#   4. Builds the signed release files in ./bin (an .aab for Google Play and an
#      .apk you can install on a device for testing).
#   5. Prints the files and their package id, target SDK and architectures.
#
# Options:
#   ./build_android.sh             build the release .aab and .apk
#   ./build_android.sh --debug     build a quick unsigned debug .apk only
#   ./build_android.sh --skip-deps do not check the system build tools
#
# The first build downloads the Android SDK and NDK (a few GB) and can take
# 30 to 60 minutes. It must run on Linux.
#
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PROJECT_DIR="$(pwd)"

MODE="release"
SKIP_DEPS=0
for arg in "$@"; do
    case "$arg" in
        --debug)     MODE="debug" ;;
        --skip-deps) SKIP_DEPS=1 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

VENV_DIR="venv"
KEYSTORE_FILE="$PROJECT_DIR/cointex-upload.keystore"
KEYSTORE_ALIAS="cointex-upload"
ENV_FILE="$PROJECT_DIR/.env"

# Make sure the venv and buildozer are ready.
if [[ ! -d "$VENV_DIR" ]]; then
    echo "venv missing, creating it with setup_venv.sh"
    ./setup_venv.sh
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade buildozer cython

# Check the Android build tools. setup_venv.sh installs them.
if [[ "$SKIP_DEPS" -eq 0 ]]; then
    missing=""
    command -v javac      >/dev/null 2>&1 || missing="$missing openjdk-17-jdk"
    command -v autoconf   >/dev/null 2>&1 || missing="$missing autoconf"
    command -v automake   >/dev/null 2>&1 || missing="$missing automake"
    command -v libtoolize >/dev/null 2>&1 || missing="$missing libtool"
    command -v cmake      >/dev/null 2>&1 || missing="$missing cmake"
    if [[ -n "$missing" ]]; then
        echo "Android build tools are missing:$missing" >&2
        echo "Run ./setup_venv.sh first, then run this script again." >&2
        exit 1
    fi
fi

# A quick debug build needs no signing.
if [[ "$MODE" == "debug" ]]; then
    echo "Building a debug apk"
    buildozer android debug
    echo "Done. Files in ./bin:"; ls -1 bin/ 2>/dev/null || true
    exit 0
fi

# Create the upload key the first time. A PKCS12 keystore (the modern default)
# uses one password for both the store and the key, so we generate a single one.
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Creating signing details in .env. Keep this file private and backed up."
    PW="$(python -c "import secrets; print(secrets.token_urlsafe(24))")"
    {
        echo "KEYSTORE_PATH=$KEYSTORE_FILE"
        echo "KEYSTORE_ALIAS=$KEYSTORE_ALIAS"
        echo "KEYSTORE_PASSWORD=$PW"
    } > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi
# shellcheck disable=SC1091
source "$ENV_FILE"

if [[ ! -f "$KEYSTORE_FILE" ]]; then
    echo "Creating the upload keystore: $KEYSTORE_FILE"
    keytool -genkeypair -v \
        -keystore "$KEYSTORE_FILE" \
        -alias "$KEYSTORE_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass "$KEYSTORE_PASSWORD" -keypass "$KEYSTORE_PASSWORD" \
        -dname "CN=Ahmed Gad, OU=CoinTex, O=CoinTex, L=Unknown, ST=Unknown, C=US"

    echo "Exporting upload_certificate.pem for Play Console"
    keytool -export -rfc \
        -keystore "$KEYSTORE_FILE" \
        -alias "$KEYSTORE_ALIAS" \
        -storepass "$KEYSTORE_PASSWORD" \
        -file "$PROJECT_DIR/upload_certificate.pem"

    echo "Back up cointex-upload.keystore and .env now. Without them you cannot"
    echo "sign new uploads. See SIGNING.md for details."
fi

# Pass the keystore to python-for-android. The key password is the same as the
# store password because the keystore is in PKCS12 format.
export P4A_RELEASE_KEYSTORE="$KEYSTORE_FILE"
export P4A_RELEASE_KEYSTORE_PASSWD="$KEYSTORE_PASSWORD"
export P4A_RELEASE_KEYALIAS="$KEYSTORE_ALIAS"
export P4A_RELEASE_KEYALIAS_PASSWD="$KEYSTORE_PASSWORD"

# python-for-android builds one file type per run, so build the aab and the apk
# in two passes. Always leave buildozer.spec set back to aab when done.
set_artifact() {
    sed -i "s/^android.release_artifact = .*/android.release_artifact = $1/" buildozer.spec
}
trap 'set_artifact aab' EXIT

echo "Building the release aab for Google Play"
set_artifact aab
buildozer android release

echo "Building the release apk for testing on a device"
set_artifact apk
buildozer android release

# Report the files.
echo ""
echo "Build finished. Files in ./bin:"
ls -1 bin/ 2>/dev/null || true

# Print package details from the apk using aapt from the downloaded SDK.
AAPT="$(find "$HOME/.buildozer" -type f -name aapt 2>/dev/null | sort | tail -1 || true)"
APK="$(ls -1 bin/*.apk 2>/dev/null | head -1 || true)"
if [[ -n "$AAPT" && -n "$APK" ]]; then
    echo ""
    echo "Details of $APK:"
    "$AAPT" dump badging "$APK" | grep -E "package:|sdkVersion:|targetSdkVersion:|native-code:" || true
fi

echo ""
echo "Next steps:"
echo "  Upload the .aab in ./bin to Google Play as a new release."
echo "  If Play rejects the version code, raise android.numeric_version in"
echo "  buildozer.spec and build again."
echo "  For signing or lost key questions, see SIGNING.md."
