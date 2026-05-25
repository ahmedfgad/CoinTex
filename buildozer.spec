[app]

# (str) Title of your application
title = CoinTex

# (str) Package name + domain  ->  application id = coin.tex.cointexreactfast
# IMPORTANT: these MUST stay exactly as published, or Google Play will treat the
# build as a different app and reject it as an update.
package.name = cointexreactfast
package.domain = coin.tex

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,wav

# (list) Directories to exclude from the package.
# PlayerGA holds the genetic-algorithm variant (needs pygad/numpy) and duplicate
# assets; it must NOT ship in the release. The rest are build/dev artifacts.
source.exclude_dirs = bin, venv, .venv, .buildozer, .git, __pycache__, PlayerGA

# (str) Application version shown to users
version = 1.2

# (list) Application requirements (release game only — no pygad/numpy here)
requirements = python3,kivy

# (str) Presplash of the application
presplash.filename = %(source.dir)s/cointex_presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/cointex_logo.png

# (str) Supported orientation (one of landscape, portrait or all)
orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1


#
# Android specific
#

# (int) Target Android API. Google Play requires app updates to target API 35
# (Android 15) as of Aug 31, 2025.
android.api = 35

# (int) Minimum API your APK / AAB will support (python-for-android needs >= 21)
android.minapi = 21

# (list) The Android archs to build for.
# 64-bit (arm64-v8a) is MANDATORY on Google Play; armeabi-v7a is kept for older
# 32-bit devices. Both ship in a single APK / AAB.
android.archs = arm64-v8a, armeabi-v7a

# (bool) Automatically accept the Android SDK licenses (non-interactive builds)
android.accept_sdk_license = True

# (str) Release artifact to build: aab, apk, or all.
# "all" gives an APK (for sideload testing) AND an AAB (for the Play upload).
android.release_artifact = all

# (int) Android versionCode. MUST be strictly greater than the versionCode of the
# build currently live on Google Play, or the upload is rejected.
# >>> VERIFY in Play Console: Release > App bundle explorer (shows version codes) <<<
# 10200 corresponds to version 1.2; raise it if the live value is already higher.
android.numeric_version = 10200

# (str) Presplash background color shown while the app loads
android.presplash_color = #000000

# NOTE on signing: release signing is supplied by build_android.sh through the
# P4A_RELEASE_KEYSTORE* environment variables, so no keystore is hardcoded here.


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Warn if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
