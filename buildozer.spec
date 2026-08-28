[app]

# Title of the application.
title = CoinTex

# Package name and domain. Together they form the application id
# coin.tex.cointexreactfast. Keep these the same as the published app or Google
# Play will treat the build as a different app.
package.name = cointexreactfast
package.domain = coin.tex

# Folder that holds main.py.
source.dir = .

# File types to include in the package. All graphics are drawn in code now, so
# the only images are the launcher icon and splash (png). Audio is wav.
source.include_exts = py,png,wav

# Folders to leave out of the package. PlayerGA is the old genetic algorithm
# version (needs pygad and numpy). audio_alternatives and tools are dev only.
source.exclude_dirs = bin, dist, build, venv, .venv, .buildozer, .git, __pycache__, tests, PlayerGA, audio_alternatives, tools, music/originals, sprite_preview, cointex_media, app_store, ios, android

# Version shown to users. This patch release updates the Android target SDK.
version = 1.4.1

# Networking uses the standard library. certifi supplies a verified CA bundle
# for the optional public-IP HTTPS lookup on mobile.
requirements = python3,kivy,certifi==2026.7.22

# The 2-player feature opens a network connection between the two devices.
android.permissions = INTERNET

# Progress is intentionally local and is not copied into Android cloud backups.
android.allow_backup = False

# Mark CoinTex as a game (so Android preserves its landscape game experience on
# large screens) and retain Kivy's legacy Back callback on API 36. Android 17
# removes this temporary Back opt-out, so revisit it before targeting API 37.
android.extra_manifest_application_arguments = android/manifest_application_attributes.xml

# Splash image shown while the app starts.
presplash.filename = %(source.dir)s/cointex_presplash.png

# App icon.
icon.filename = %(source.dir)s/cointex_logo.png

# Screen orientation.
orientation = landscape

# Run the app full screen.
fullscreen = 1


# Android settings

# Target Android 16. Google Play requires updates to target API 36 from
# August 31, 2026.
android.api = 36

# Lowest Android version the app runs on. python-for-android needs 21 or higher.
android.minapi = 21

# NDK recommended by the pinned python-for-android release below.
android.ndk = 28c

# Build for 64-bit and 32-bit. Google Play requires the 64-bit arm64-v8a.
android.archs = arm64-v8a, armeabi-v7a

# Accept the Android SDK licenses so the build does not stop to ask.
android.accept_sdk_license = True

# Release file to build: aab or apk. The Play Store upload uses the aab.
# build_android.sh switches this when it also builds the apk for testing.
android.release_artifact = aab

# Version code. It must be higher than the version code already on Google Play,
# or the upload is rejected. Check the current value in Play Console under
# Release, App bundle explorer.
android.numeric_version = 10401

# Background color of the splash screen.
android.presplash_color = #000000

# Release signing is passed in by build_android.sh through the P4A_RELEASE_KEYSTORE
# environment variables, so no keystore is written here.

# Pin the python-for-android release that includes Android Gradle Plugin 8.11,
# Gradle 8.14.3 and NDK 28c support. Those versions can compile/target API 36.
# The v2026.05.09 release commit lives on the master branch; pinning the commit
# prevents a later branch change from silently changing the release toolchain.
p4a.branch = master
p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831


[buildozer]

# Log level. 2 shows full command output.
log_level = 2

# Warn if buildozer runs as root.
warn_on_root = 1
