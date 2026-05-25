#!/usr/bin/env bash
#
# build_android.sh — Build the CoinTex Android APK + AAB ready for Google Play.
#
# What it does:
#   1. Ensures the Python 3.12 venv exists and installs buildozer + Cython.
#   2. Checks for the Android build toolchain (JDK 17, autotools, ...) and offers
#      to apt-install anything missing (needs sudo).
#   3. Creates a release UPLOAD keystore (once) and exports its certificate so you
#      can register it with Google Play App Signing if needed (see SIGNING.md).
#   4. Runs buildozer to produce signed release artifacts in ./bin
#      (an .aab for the Play Store upload and an .apk for sideload testing).
#   5. Prints the artifacts and their package id / versionCode / target SDK.
#
# Usage:
#   ./build_android.sh                # full release build (apk + aab)
#   ./build_android.sh --debug        # quick unsigned debug apk (sanity check)
#   ./build_android.sh --skip-deps    # don't touch system packages
#
# NOTE: the FIRST run downloads the Android SDK/NDK (several GB) and can take
#       30–60+ minutes. Must run on Linux (buildozer does not run on Windows/macOS).
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

# ---------------------------------------------------------------------------
# 1. Virtual environment + buildozer
# ---------------------------------------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
    echo ">> venv missing; creating it via setup_venv.sh"
    ./setup_venv.sh
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ">> Ensuring buildozer + Cython are installed"
python -m pip install --upgrade buildozer cython

# ---------------------------------------------------------------------------
# 2. Verify the Android build toolchain (installed by setup_venv.sh)
# ---------------------------------------------------------------------------
# The system packages (JDK, autotools, cmake, the zlib fix, ...) are installed by
# setup_venv.sh — the single source of truth. Here we just check they're present.
if [[ "$SKIP_DEPS" -eq 0 ]]; then
    missing=""
    command -v javac      >/dev/null 2>&1 || missing="$missing openjdk-17-jdk"
    command -v autoconf   >/dev/null 2>&1 || missing="$missing autoconf"
    command -v automake   >/dev/null 2>&1 || missing="$missing automake"
    command -v libtoolize >/dev/null 2>&1 || missing="$missing libtool"
    command -v cmake      >/dev/null 2>&1 || missing="$missing cmake"
    if [[ -n "$missing" ]]; then
        echo "ERROR: Android build tools are missing:$missing" >&2
        echo "Run ./setup_venv.sh first — it installs the full toolchain (JDK," >&2
        echo "autotools, cmake, the SDL2 runtime, and the zlib version fix)," >&2
        echo "then re-run ./build_android.sh" >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# 3. Debug build short-circuit (no signing needed)
# ---------------------------------------------------------------------------
if [[ "$MODE" == "debug" ]]; then
    echo ">> Building DEBUG apk (unsigned, for sanity testing)"
    buildozer android debug
    echo ">> Done. Artifacts:"; ls -1 bin/ 2>/dev/null || true
    exit 0
fi

# ---------------------------------------------------------------------------
# 4. Release upload keystore
# ---------------------------------------------------------------------------
if [[ ! -f "$ENV_FILE" ]]; then
    echo ">> Generating signing credentials in .env (keep this file SECRET + BACKED UP)"
    gen_pw() { python -c "import secrets; print(secrets.token_urlsafe(24))"; }
    {
        echo "KEYSTORE_PATH=$KEYSTORE_FILE"
        echo "KEYSTORE_ALIAS=$KEYSTORE_ALIAS"
        echo "KEYSTORE_PASSWORD=$(gen_pw)"
        echo "KEY_PASSWORD=$(gen_pw)"
    } > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi
# shellcheck disable=SC1091
source "$ENV_FILE"

if [[ ! -f "$KEYSTORE_FILE" ]]; then
    echo ">> Creating release upload keystore: $KEYSTORE_FILE"
    keytool -genkeypair -v \
        -keystore "$KEYSTORE_FILE" \
        -alias "$KEYSTORE_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass "$KEYSTORE_PASSWORD" -keypass "$KEY_PASSWORD" \
        -dname "CN=Ahmed Gad, OU=CoinTex, O=CoinTex, L=Unknown, ST=Unknown, C=US"

    echo ">> Exporting upload_certificate.pem (for Play App Signing 'upload key reset')"
    keytool -export -rfc \
        -keystore "$KEYSTORE_FILE" \
        -alias "$KEYSTORE_ALIAS" \
        -storepass "$KEYSTORE_PASSWORD" \
        -file "$PROJECT_DIR/upload_certificate.pem"

    cat <<'WARN'

   *********************************************************************
   *  BACK UP cointex-upload.keystore AND .env SOMEWHERE SAFE NOW.    *
   *  Losing them again means losing your upload key. See SIGNING.md  *
   *  for how to register upload_certificate.pem with Google Play.    *
   *********************************************************************
WARN
fi

# Hand the keystore to python-for-android via the documented env vars.
export P4A_RELEASE_KEYSTORE="$KEYSTORE_FILE"
export P4A_RELEASE_KEYSTORE_PASSWD="$KEYSTORE_PASSWORD"
export P4A_RELEASE_KEYALIAS="$KEYSTORE_ALIAS"
export P4A_RELEASE_KEYALIAS_PASSWD="$KEY_PASSWORD"

# ---------------------------------------------------------------------------
# 5. Release build
# ---------------------------------------------------------------------------
echo ">> Building signed RELEASE artifacts (apk + aab) — this can take a while"
buildozer android release

# ---------------------------------------------------------------------------
# 6. Report + verify
# ---------------------------------------------------------------------------
echo ""
echo ">> Build finished. Artifacts in ./bin :"
ls -1 bin/ 2>/dev/null || true

# Locate aapt from the SDK buildozer downloaded, to print build metadata.
AAPT="$(find "$HOME/.buildozer" -type f -name aapt 2>/dev/null | sort | tail -1 || true)"
APK="$(ls -1 bin/*.apk 2>/dev/null | head -1 || true)"
if [[ -n "$AAPT" && -n "$APK" ]]; then
    echo ""
    echo ">> APK metadata ($APK):"
    "$AAPT" dump badging "$APK" | grep -E "package:|sdkVersion:|targetSdkVersion:|native-code:" || true
fi

cat <<EOF

Next steps:
  • Upload the .aab in ./bin to Google Play Console (new release).
  • If Play rejects the versionCode, raise android.numeric_version in
    buildozer.spec above the live value and rebuild.
  • If your signing/upload key is the problem, read SIGNING.md.
EOF
