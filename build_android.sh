#!/usr/bin/env bash
#
# Builds the CoinTex Android package, ready to upload to Google Play.
#
# What it does:
#   1. Activates the venv and installs the pinned Android packaging tools.
#   2. Checks that the Android build tools are present (installed by setup_venv.sh).
#   3. Creates a release upload key the first time, and exports its certificate.
#   4. Builds the signed release files in ./bin (an .aab for Google Play and an
#      .apk you can install on a device for testing).
#   5. Prints the files and their package id, target SDK and architectures.
#
# Options:
#   ./build_android.sh             build the release .aab and .apk
#   ./build_android.sh --debug     build a quick debug-key-signed .apk only
#   ./build_android.sh --skip-deps do not check the system build tools
#
# The first build downloads the Android SDK and NDK (a few GB) and can take
# 30 to 60 minutes. It must run on Linux.
#
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PROJECT_DIR="$(pwd)"
PIP_CONSTRAINT_FILE="$PROJECT_DIR/android-pip-constraints.txt"

# python-for-android creates a temporary Python 3.14 environment and upgrades
# pip while assembling pure-Python dependencies. pip 26 currently leaves that
# environment with mixed 25.x/26.x internals, so keep the known-good version
# until the upstream packaging path supports pip 26.
export PIP_CONSTRAINT="$PIP_CONSTRAINT_FILE"

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
# Google Play currently expects this upload certificate. Keeping the public
# fingerprint here prevents a locally generated or unrelated key from producing
# an AAB that looks valid but cannot be uploaded to the existing app.
EXPECTED_UPLOAD_SHA1="C681B685589182C45C72F6957167A3E875AF6339"

# Make sure the venv and buildozer are ready.
if [[ ! -d "$VENV_DIR" ]]; then
    echo "venv missing, creating it with setup_venv.sh"
    ./setup_venv.sh
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade -r requirements-android.txt

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
KEYSTORE_FILE="${KEYSTORE_PATH:-$KEYSTORE_FILE}"

if [[ ! -f "$KEYSTORE_FILE" ]]; then
    echo "Creating the upload keystore: $KEYSTORE_FILE"
    keytool -genkeypair -v \
        -keystore "$KEYSTORE_FILE" \
        -alias "$KEYSTORE_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass "$KEYSTORE_PASSWORD" -keypass "$KEYSTORE_PASSWORD" \
        -dname "CN=Ahmed Gad, OU=CoinTex, O=CoinTex, L=Unknown, ST=Unknown, C=US"

    echo "Back up cointex-upload.keystore and .env now. Without them you cannot"
    echo "sign new uploads. See SIGNING.md for details."
fi

ACTUAL_UPLOAD_SHA1="$(
    keytool -exportcert \
        -keystore "$KEYSTORE_FILE" \
        -alias "$KEYSTORE_ALIAS" \
        -storepass "$KEYSTORE_PASSWORD" 2>/dev/null \
        | openssl dgst -sha1 -r | awk '{print toupper($1)}'
)"

# Export even a replacement candidate before enforcing the recorded Play
# fingerprint. This gives the owner the PEM needed for an upload-key reset,
# while the mismatch guard still prevents an unusable AAB from being built.
keytool -export -rfc \
    -keystore "$KEYSTORE_FILE" \
    -alias "$KEYSTORE_ALIAS" \
    -storepass "$KEYSTORE_PASSWORD" \
    -file "$PROJECT_DIR/upload_certificate.pem" >/dev/null

if [[ "$ACTUAL_UPLOAD_SHA1" != "$EXPECTED_UPLOAD_SHA1" ]]; then
    echo "Refusing to build with the wrong Google Play upload key." >&2
    echo "Expected SHA-1: $EXPECTED_UPLOAD_SHA1" >&2
    echo "Actual SHA-1:   $ACTUAL_UPLOAD_SHA1" >&2
    echo "Restore the matching CoinTex key or complete an upload-key reset." >&2
    echo "The reset certificate is upload_certificate.pem." >&2
    echo "See SIGNING.md for the recovery steps." >&2
    exit 1
fi
echo "Verified the Google Play upload certificate: $ACTUAL_UPLOAD_SHA1"

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
AAPT="$(find "$HOME/.buildozer" -type f -name aapt 2>/dev/null | sort -V | tail -1 || true)"
APK="$(ls -1t bin/*release*.apk 2>/dev/null | head -1 || true)"
ABUNDLE="$(ls -1t bin/*release*.aab 2>/dev/null | head -1 || true)"
test -n "$AAPT" || { echo "Android aapt was not found" >&2; exit 1; }
test -n "$APK" || { echo "Release APK was not found" >&2; exit 1; }
test -n "$ABUNDLE" || { echo "Release AAB was not found" >&2; exit 1; }
echo ""
echo "Details of $APK:"
"$AAPT" dump badging "$APK" | grep -E "package:|sdkVersion:|targetSdkVersion:|native-code:"
"$AAPT" dump badging "$APK" | grep -F "targetSdkVersion:'36'" >/dev/null
python tools/validate_android_artifact.py "$APK"
python tools/validate_android_artifact.py "$ABUNDLE"

echo ""
echo "Next steps:"
echo "  Upload the .aab in ./bin to Google Play as a new release."
echo "  If Play rejects the version code, raise android.numeric_version in"
echo "  buildozer.spec and build again."
echo "  For signing or lost key questions, see SIGNING.md."
