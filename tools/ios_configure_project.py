#!/usr/bin/env python3
"""Apply CoinTex App Store metadata to a generated kivy-ios Xcode project."""

from __future__ import annotations

import argparse
import plistlib
import shutil
from pathlib import Path


def read_xcconfig(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def exactly_one(paths: list[Path], what: str) -> Path:
    if len(paths) != 1:
        raise SystemExit("Expected one {}, found {}: {}".format(
            what, len(paths), ", ".join(str(path) for path in paths)))
    return paths[0]


def configure_plist(plist_path: Path, settings: dict[str, str]) -> None:
    with plist_path.open("rb") as handle:
        info = plistlib.load(handle)

    landscape_orientations = [
        "UIInterfaceOrientationLandscapeLeft",
        "UIInterfaceOrientationLandscapeRight",
    ]
    info.update({
        "CFBundleDisplayName": settings["APP_DISPLAY_NAME"],
        "CFBundleName": settings["PRODUCT_NAME"],
        "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
        "CFBundleShortVersionString": "$(MARKETING_VERSION)",
        "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
        "ITSAppUsesNonExemptEncryption": False,
        "LSRequiresIPhoneOS": True,
        "NSLocalNetworkUsageDescription": (
            "CoinTex uses the local network to play with a nearby device."
        ),
        "UIApplicationSupportsIndirectInputEvents": True,
        "UILaunchStoryboardName": "Launch Screen",
        "UIRequiredDeviceCapabilities": ["arm64"],
        "UIStatusBarHidden": True,
        "UISupportedInterfaceOrientations": landscape_orientations,
        "UISupportedInterfaceOrientations~ipad": landscape_orientations,
    })
    info.pop("NSAppTransportSecurity", None)

    with plist_path.open("wb") as handle:
        plistlib.dump(info, handle, fmt=plistlib.FMT_XML, sort_keys=False)


def configure_project(project_file: Path, privacy_file: Path,
                      app_source: Path, settings: dict[str, str]) -> None:
    try:
        from pbxproj import XcodeProject
        from pbxproj.pbxextensions.ProjectFiles import ProjectFiles
    except ImportError as error:
        raise SystemExit(
            "pbxproj is missing; install requirements-ios.txt first"
        ) from error

    project = XcodeProject.load(str(project_file))
    target_name = project_file.parent.stem
    project_dir = project_file.parent.parent

    for key in (
        "PRODUCT_NAME",
        "PRODUCT_BUNDLE_IDENTIFIER",
        "MARKETING_VERSION",
        "CURRENT_PROJECT_VERSION",
        "IPHONEOS_DEPLOYMENT_TARGET",
        "TARGETED_DEVICE_FAMILY",
        "SUPPORTS_MACCATALYST",
        "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD",
        "COPY_PHASE_STRIP",
        "STRIP_INSTALLED_PRODUCT",
        "DEAD_CODE_STRIPPING",
        "ENABLE_BITCODE",
        "ASSETCATALOG_COMPILER_APPICON_NAME",
    ):
        project.set_flags(key, settings[key], target_name=target_name)

    project.set_flags("CODE_SIGN_STYLE", "Automatic", target_name=target_name)
    project.set_flags("SUPPORTED_PLATFORMS", "iphoneos iphonesimulator",
                      target_name=target_name)

    for key in (
        "CODE_SIGN_RESOURCE_RULES_PATH",
        "CODE_SIGN_IDENTITY",
        "CODE_SIGN_IDENTITY[sdk=iphoneos*]",
        "PROVISIONING_PROFILE",
        "PROVISIONING_PROFILE[sdk=iphoneos*]",
        "PROVISIONING_PROFILE_SPECIFIER",
    ):
        project.remove_flags(key, None, target_name=target_name)

    # kivy-ios writes the source directory's absolute path into a build phase.
    # Store a clean runtime-source copy inside the generated project and make
    # the build phase relative, so a project downloaded from CI remains usable
    # on a different Mac instead of referring to the GitHub runner's old path.
    portable_source = project_dir / "AppSource"
    if portable_source.exists():
        shutil.rmtree(portable_source)
    shutil.copytree(app_source, portable_source)
    for phase in project.objects.get_objects_in_section("PBXShellScriptBuildPhase"):
        if "rsync -av --delete" in getattr(phase, "shellScript", ""):
            phase.shellScript = (
                'rsync -av --delete "$PROJECT_DIR/AppSource"/ '
                '"$PROJECT_DIR"/YourApp'
            )

    destination = project_dir / "PrivacyInfo.xcprivacy"
    shutil.copyfile(privacy_file, destination)
    resources = project.get_or_create_group("Resources")
    ProjectFiles._FILE_TYPES[".xcprivacy"] = (
        "text.xml", "PBXResourcesBuildPhase"
    )
    project.add_file(str(destination), parent=resources, force=False,
                     target_name=target_name)
    project.save()

    saved = project_file.read_text(encoding="utf-8")
    if "PrivacyInfo.xcprivacy in Resources" not in saved:
        raise SystemExit("PrivacyInfo.xcprivacy was not added to app resources")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--config", type=Path,
                        default=Path("ios/CoinTex.xcconfig"))
    parser.add_argument("--privacy", type=Path,
                        default=Path("ios/PrivacyInfo.xcprivacy"))
    parser.add_argument("--app-source", type=Path,
                        default=Path(".ios-app"))
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    config_path = args.config.resolve()
    privacy_path = args.privacy.resolve()
    app_source = args.app_source.resolve()
    if not (app_source / "main.py").is_file():
        raise SystemExit(f"Staged app source is missing main.py: {app_source}")
    settings = read_xcconfig(config_path)
    required = {
        "APP_DISPLAY_NAME", "PRODUCT_NAME", "PRODUCT_BUNDLE_IDENTIFIER",
        "MARKETING_VERSION", "CURRENT_PROJECT_VERSION",
        "IPHONEOS_DEPLOYMENT_TARGET", "TARGETED_DEVICE_FAMILY",
        "SUPPORTS_MACCATALYST", "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD",
        "COPY_PHASE_STRIP", "STRIP_INSTALLED_PRODUCT",
        "DEAD_CODE_STRIPPING", "ENABLE_BITCODE",
        "ASSETCATALOG_COMPILER_APPICON_NAME",
    }
    missing = sorted(required.difference(settings))
    if missing:
        raise SystemExit("Missing xcconfig values: {}".format(", ".join(missing)))

    xcodeproj = exactly_one(list(project_dir.glob("*.xcodeproj")),
                            "Xcode project")
    project_file = xcodeproj / "project.pbxproj"
    plist_path = exactly_one(list(project_dir.glob("*-Info.plist")),
                             "Info.plist")

    configure_plist(plist_path, settings)
    configure_project(project_file, privacy_path, app_source, settings)
    print("Configured {} for {} {} ({})".format(
        xcodeproj.name,
        settings["PRODUCT_BUNDLE_IDENTIFIER"],
        settings["MARKETING_VERSION"],
        settings["CURRENT_PROJECT_VERSION"],
    ))


if __name__ == "__main__":
    main()
