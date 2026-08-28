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
# Requires `sips` (built into macOS) for launch-image dimensions and Pillow
# (installed with kivy-ios) for an opaque App Store icon catalog.

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
    python3 - "$LOGO" "$APPICON" <<'PY'
import json
import os
import sys

from PIL import Image

source, destination = sys.argv[1:]
logo = Image.open(source).convert("RGBA")
if logo.width != logo.height or logo.width < 512:
    raise SystemExit("iOS icon source must be square and at least 512x512")

# Apple rejects the 1024px marketing icon if the PNG contains an alpha channel,
# even when every pixel is opaque. Flatten every output to RGB.
background = Image.new("RGBA", logo.size, (35, 75, 155, 255))
logo = Image.alpha_composite(background, logo).convert("RGB")
resampling = getattr(Image, "Resampling", Image).LANCZOS

icons = [
    ("iphone", "20x20", "2x", 40, "icon-20@2x.png"),
    ("iphone", "20x20", "3x", 60, "icon-20@3x.png"),
    ("iphone", "29x29", "2x", 58, "icon-29@2x.png"),
    ("iphone", "29x29", "3x", 87, "icon-29@3x.png"),
    ("iphone", "40x40", "2x", 80, "icon-40@2x.png"),
    ("iphone", "40x40", "3x", 120, "icon-40@3x.png"),
    ("iphone", "60x60", "2x", 120, "icon-60@2x.png"),
    ("iphone", "60x60", "3x", 180, "icon-60@3x.png"),
    ("ipad", "20x20", "1x", 20, "icon-ipad-20.png"),
    ("ipad", "20x20", "2x", 40, "icon-ipad-20@2x.png"),
    ("ipad", "29x29", "1x", 29, "icon-ipad-29.png"),
    ("ipad", "29x29", "2x", 58, "icon-ipad-29@2x.png"),
    ("ipad", "40x40", "1x", 40, "icon-ipad-40.png"),
    ("ipad", "40x40", "2x", 80, "icon-ipad-40@2x.png"),
    ("ipad", "76x76", "1x", 76, "icon-ipad-76.png"),
    ("ipad", "76x76", "2x", 152, "icon-ipad-76@2x.png"),
    ("ipad", "83.5x83.5", "2x", 167, "icon-ipad-83.5@2x.png"),
    ("ios-marketing", "1024x1024", "1x", 1024, "icon-1024.png"),
]

images = []
for idiom, points, scale, pixels, filename in icons:
    output = logo.resize((pixels, pixels), resampling)
    output.save(os.path.join(destination, filename), "PNG", optimize=True)
    images.append({
        "idiom": idiom,
        "size": points,
        "scale": scale,
        "filename": filename,
    })

with open(os.path.join(destination, "Contents.json"), "w", encoding="utf-8") as handle:
    json.dump({"images": images, "info": {"version": 1, "author": "xcode"}},
              handle, indent=2)
    handle.write("\n")
PY
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
