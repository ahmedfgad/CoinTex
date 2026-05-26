#!/usr/bin/env bash
#
# Replaces the placeholder Kivy-logo assets in a freshly created kivy-ios
# Xcode project with the CoinTex logo (home-screen icon) and presplash
# (launch screen). Run after `toolchain create` and before `xcodebuild`.
#
# Why this is needed:
#   - buildozer.spec icon.filename and presplash.filename only apply to the
#     Android build. kivy-ios reads neither, so the iOS template's defaults
#     (the Kivy logo in icon.png + an empty AppIcon.appiconset) are what ends
#     up in the .ipa unless we replace them here.
#
# Usage:
#   tools/ios_apply_assets.sh <project-dir> <logo.png> <presplash.png>
#
# Requires `sips` (built into macOS) to resize the icon.

set -euo pipefail

PROJ_DIR="${1:?missing project dir}"
LOGO="${2:?missing logo path}"
PRESPLASH="${3:?missing presplash path}"

if ! command -v sips >/dev/null 2>&1; then
    echo "sips not found - this script must run on macOS." >&2
    exit 1
fi
for path in "$PROJ_DIR" "$LOGO" "$PRESPLASH"; do
    if [ ! -e "$path" ]; then
        echo "Path not found: $path" >&2
        exit 1
    fi
done

echo "Applying CoinTex iOS assets to $PROJ_DIR"

# 1. Replace icon.png at the project root with the presplash image. The launch
#    screen storyboard renders this file. (Step 2 below populates the asset
#    catalog so the home-screen icon comes from there, not from this file.)
cp "$PRESPLASH" "$PROJ_DIR/icon.png"
PW=$(sips -g pixelWidth  "$PRESPLASH" | awk '/pixelWidth/  {print $2}')
PH=$(sips -g pixelHeight "$PRESPLASH" | awk '/pixelHeight/ {print $2}')

# 2. Populate AppIcon.appiconset from the CoinTex logo. The kivy-ios template
#    ships an empty catalog, so without this iOS shows a placeholder icon (or
#    falls back to icon.png, which is now the presplash and not square).
APPICON=$(find "$PROJ_DIR" -type d -name AppIcon.appiconset | head -1)
if [ -n "$APPICON" ]; then
    sips -z 58  58   "$LOGO" --out "$APPICON/icon-29@2x.png" >/dev/null
    sips -z 87  87   "$LOGO" --out "$APPICON/icon-29@3x.png" >/dev/null
    sips -z 80  80   "$LOGO" --out "$APPICON/icon-40@2x.png" >/dev/null
    sips -z 120 120  "$LOGO" --out "$APPICON/icon-40@3x.png" >/dev/null
    sips -z 120 120  "$LOGO" --out "$APPICON/icon-60@2x.png" >/dev/null
    sips -z 180 180  "$LOGO" --out "$APPICON/icon-60@3x.png" >/dev/null
    cat > "$APPICON/Contents.json" <<'JSON'
{
  "images" : [
    {"idiom":"iphone","size":"29x29","scale":"2x","filename":"icon-29@2x.png"},
    {"idiom":"iphone","size":"29x29","scale":"3x","filename":"icon-29@3x.png"},
    {"idiom":"iphone","size":"40x40","scale":"2x","filename":"icon-40@2x.png"},
    {"idiom":"iphone","size":"40x40","scale":"3x","filename":"icon-40@3x.png"},
    {"idiom":"iphone","size":"60x60","scale":"2x","filename":"icon-60@2x.png"},
    {"idiom":"iphone","size":"60x60","scale":"3x","filename":"icon-60@3x.png"}
  ],
  "info" : { "version" : 1, "author" : "xcode" }
}
JSON
else
    echo "AppIcon.appiconset not found - leaving icon catalog alone." >&2
fi

# 3. Rewrite Launch Screen.storyboard so the presplash fills the screen with a
#    black background. The template ships a small 240x128 centered image view,
#    designed for the Kivy logo, which is the wrong size for our presplash.
STORY=$(find "$PROJ_DIR" -type f -name "Launch Screen.storyboard" | head -1)
if [ -n "$STORY" ]; then
    cat > "$STORY" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<document type="com.apple.InterfaceBuilder3.CocoaTouch.Storyboard.XIB" version="3.0" toolsVersion="21507" targetRuntime="iOS.CocoaTouch" propertyAccessControl="none" useAutolayout="YES" launchScreen="YES" useTraitCollections="YES" useSafeAreas="YES" colorMatched="YES" initialViewController="01J-lp-oVM">
    <device id="retina6_12" orientation="landscape" appearance="light"/>
    <dependencies>
        <deployment identifier="iOS"/>
        <plugIn identifier="com.apple.InterfaceBuilder.IBCocoaTouchPlugin" version="21505"/>
        <capability name="Safe area layout guides" minToolsVersion="9.0"/>
        <capability name="documents saved in the Xcode 8 format" minToolsVersion="8.0"/>
    </dependencies>
    <scenes>
        <scene sceneID="EHf-IW-A2E">
            <objects>
                <viewController id="01J-lp-oVM" sceneMemberID="viewController">
                    <view key="view" contentMode="scaleToFill" id="Ze5-6b-2t3">
                        <rect key="frame" x="0.0" y="0.0" width="852" height="393"/>
                        <autoresizingMask key="autoresizingMask" widthSizable="YES" heightSizable="YES"/>
                        <subviews>
                            <imageView clipsSubviews="YES" userInteractionEnabled="NO" contentMode="scaleAspectFit" fixedFrame="YES" image="icon.png" translatesAutoresizingMaskIntoConstraints="NO" id="pre-im-vw1">
                                <rect key="frame" x="0.0" y="0.0" width="852" height="393"/>
                                <autoresizingMask key="autoresizingMask" widthSizable="YES" heightSizable="YES"/>
                            </imageView>
                        </subviews>
                        <viewLayoutGuide key="safeArea" id="Bcu-3y-fUS"/>
                        <color key="backgroundColor" white="0.0" alpha="1" colorSpace="custom" customColorSpace="genericGamma22GrayColorSpace"/>
                    </view>
                </viewController>
                <placeholder placeholderIdentifier="IBFirstResponder" id="iYj-Kq-Ea1" userLabel="First Responder" sceneMemberID="firstResponder"/>
            </objects>
            <point key="canvasLocation" x="53" y="375"/>
        </scene>
    </scenes>
    <resources>
        <image name="icon.png" width="$PW" height="$PH"/>
    </resources>
</document>
EOF
else
    echo "Launch Screen.storyboard not found - leaving launch screen alone." >&2
fi

echo "iOS assets applied."
