#!/usr/bin/env python3
"""Fail if a built CoinTex .app is missing App Store-critical metadata."""

from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path

from ios_configure_project import read_xcconfig


def fail(message: str) -> None:
    raise SystemExit("iOS validation failed: " + message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    parser.add_argument("--config", type=Path,
                        default=Path("ios/CoinTex.xcconfig"))
    parser.add_argument("--signed", action="store_true")
    args = parser.parse_args()

    app = args.app.resolve()
    settings = read_xcconfig(args.config.resolve())
    info_path = app / "Info.plist"
    privacy_path = app / "PrivacyInfo.xcprivacy"
    if not info_path.is_file():
        fail("Info.plist is missing")
    if not privacy_path.is_file():
        fail("PrivacyInfo.xcprivacy is missing from the app-bundle root")
    if not (app / "Assets.car").is_file():
        fail("compiled asset catalog is missing")

    with info_path.open("rb") as handle:
        info = plistlib.load(handle)
    with privacy_path.open("rb") as handle:
        privacy = plistlib.load(handle)

    expected = {
        "CFBundleDisplayName": settings["APP_DISPLAY_NAME"],
        "CFBundleIdentifier": settings["PRODUCT_BUNDLE_IDENTIFIER"],
        "CFBundleShortVersionString": settings["MARKETING_VERSION"],
        "CFBundleVersion": settings["CURRENT_PROJECT_VERSION"],
        "MinimumOSVersion": settings["IPHONEOS_DEPLOYMENT_TARGET"],
    }
    for key, value in expected.items():
        if str(info.get(key)) != value:
            fail(f"{key} is {info.get(key)!r}, expected {value!r}")

    if info.get("UIDeviceFamily") != [1, 2]:
        fail("UIDeviceFamily must include iPhone and iPad ([1, 2])")
    landscape = {
        "UIInterfaceOrientationLandscapeLeft",
        "UIInterfaceOrientationLandscapeRight",
    }
    if set(info.get("UISupportedInterfaceOrientations", [])) != landscape:
        fail("iPhone orientations must be landscape-only")
    if set(info.get("UISupportedInterfaceOrientations~ipad", [])) != landscape:
        fail("iPad orientations must be landscape-only")
    if info.get("ITSAppUsesNonExemptEncryption") is not False:
        fail("ITSAppUsesNonExemptEncryption must be false")
    if not info.get("NSLocalNetworkUsageDescription"):
        fail("local-network purpose text is missing")
    if info.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads"):
        fail("arbitrary network loads must not be enabled")
    if not str(info.get("DTSDKName", "")).startswith("iphoneos26"):
        fail("the app was not built with the iOS 26 SDK")
    if privacy.get("NSPrivacyTracking") is not False:
        fail("privacy manifest must declare tracking=false")
    if privacy.get("NSPrivacyCollectedDataTypes") != []:
        fail("privacy manifest data collection does not match CoinTex policy")
    if not privacy.get("NSPrivacyAccessedAPITypes"):
        fail("required-reason API declarations are missing")

    executable = app / info.get("CFBundleExecutable", "")
    if not executable.is_file():
        fail("app executable is missing")
    archs = subprocess.run(
        ["lipo", "-archs", str(executable)], check=True,
        capture_output=True, text=True,
    ).stdout.split()
    if "arm64" not in archs:
        fail("arm64 executable slice is missing")

    if args.signed:
        if not (app / "embedded.mobileprovision").is_file():
            fail("embedded App Store provisioning profile is missing")
        subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", str(app)],
            check=True,
        )

    print("Validated {} {} ({}) for iPhone and iPad; SDK {}".format(
        info["CFBundleIdentifier"], info["CFBundleShortVersionString"],
        info["CFBundleVersion"], info["DTSDKName"],
    ))


if __name__ == "__main__":
    main()
