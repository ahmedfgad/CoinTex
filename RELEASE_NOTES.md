# CoinTex 1.4.1

CoinTex is a top-down arcade game written entirely in Python with [Kivy](https://kivy.org). Move your character around each level to collect all the coins before the timer runs out, while dodging monsters and fire and shooting your way through. The same Python codebase runs on Windows, macOS, Linux, Android and iPhone, and every screen and all of the graphics are drawn in code.

This patch release updates the Android packaging configuration for Google Play's Android 16 requirement, prepares the iPhone App Store release path, and includes a cross-platform usability and reliability pass.

## What's new in 1.4.1

- Android now targets Android 16 (API level 36) for Google Play update compliance.
- The Buildozer/python-for-android toolchain is pinned to API 36-capable releases with NDK r28c, and generated artifacts are checked for target SDK, ABIs, and 16 KB native-library alignment.
- Android now declares the game category, preserves Kivy's Back handling on API 36, and keeps progress out of Android cloud backups.
- The gameplay HUD has higher-contrast text panels, clearer Pause/Leave controls, safe margins for notches and gesture areas, and player spawns that stay clear of the lower controls.
- Desktop and Apple-silicon Mac users can move with WASD/arrow keys and fire with Space; Android Back and desktop Escape now navigate safely.
- Backgrounding pauses single-player without consuming the timer or health. Multiplayer closes cleanly rather than leaving a stalled peer connection.
- Save loading now recovers safely from truncated or malformed values, and peer messages/coordinates are bounded before reaching the game loop.
- Settings show an exact volume percentage and confirm when campaign progress has been reset.
- The Auto Player sends movement changes through Kivy's main thread, and transient visual effects are cleaned up between levels.
- An App Store-ready iPhone project path now includes current Xcode/iOS SDK checks, metadata, screenshots, privacy declarations, protected signing automation, and local archive validation.

## What's new in 1.4

- New background music. Every track was recomposed and re-rendered with GM-soundfont instruments, for the menu and all six worlds, replacing the previous tracks.
- Coin-collect "+N" pop. Picking up coins now shows an animated "+N", in both single-player and multiplayer, where each device pops only its own pickups.
- Desktop builds for Windows, Linux and macOS. CoinTex now packages into a standalone desktop app, with no Python install needed to play.
- Multiplayer fix on mobile. Fetching the host's public IP now works on phones, so the internet-address join path behaves on mobile.
- Interface polish. A redesigned roadmap screen, a main-menu fix, and the CoinTex logo now shows correctly on iPhone and Windows.
- Automated releases. Tagging a release builds and publishes every platform from one workflow.

## Features

- 6 worlds, 60 levels. Meadow, Desert, Ocean, Cavern, Volcano and Space, ten timed levels each. Difficulty comes from smarter behaviour rather than more clutter, so it stays smooth on a phone.
- Collect and survive. Grab every coin before the timer ends. Your health bar drains on contact with monsters and fire.
- Escalating hazards. Monsters start chasing (and glow red) from world 4, fire grows and shrinks as it sweeps from world 3, and a rare freeze clock stops every monster for a few seconds.
- Auto-aiming gun. Tap to shoot and it targets the nearest monster on its own. From world 4 it reloads itself, with a countdown on the button.
- Star ratings. Finish with more health left to earn up to three stars per level.
- Tutorial and Guide. An interactive tutorial runs on first play and is replayable from the menu, and the Guide screen lists every element with the in-game icons.
- Auto Player. Tap Auto and a small genetic algorithm plays the level for you, steering toward coins, dodging hazards, shooting chasers and racing the timer.
- Multiplayer, Co-op and Versus. Two people play in the same arena over the network. In Co-op you share one goal and clear the coins together; in Versus you race for the same coins and the higher total wins. It works on the same Wi-Fi with no setup, or over the internet with port forwarding, and the networking uses only the Python standard library.
- Drawn in code. No image files ship at all; every screen and sprite is rendered in code, and only the short music and effect sounds are bundled.

## Downloads

- Android: on [Google Play](https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast). You can also sideload the production-signed `CoinTex-android.apk` below; turn on "install unknown apps" first. Android only accepts it as an update when the installed copy uses the same signing certificate.
- Windows (`CoinTex-windows.exe`): download and run. SmartScreen may warn on an unsigned app; choose "More info" then "Run anyway".
- macOS (`CoinTex-macos.zip`): unzip and open CoinTex.app. On first launch, right-click the app and choose Open to get past Gatekeeper.
- Linux (`CoinTex-linux`): run `chmod +x CoinTex-linux`, then start it. It is a single self-contained file.
- iPhone (`CoinTex-unsigned.ipa`): sideload with [AltStore](https://altstore.io) or Sideloadly, which re-sign it with your own Apple ID. See IOS_INSTALL.md.
- iPhone, Xcode (`CoinTex-xcode-project.zip`): a portable, App Store-configured project. Open it on a Mac, select your team, and test it on a real iPhone.

The official Apple App Store release is being prepared separately. It requires the Apple Developer account, private distribution credentials, TestFlight testing, and App Review; the signed IPA is never attached to a normal public build by default.

The signed Google Play `.aab` is not attached here. It needs the private upload keystore and is built separately with `./build_android.sh`.

## How to play

- Tap anywhere and your character walks there.
- Collect every coin to finish a level and unlock the next.
- Your health bar (top left) drains on contact with monsters and fire. At zero you lose the level.
- Tap the gun button to shoot the nearest monster. Grab a freeze clock when it appears to stop every monster briefly.
- Finish with more health left to earn more stars.

A short tutorial runs the first time you play, and "How to play" and "Guide" on the main menu cover the rest.

## Run from source

Requires Python 3.12 (developed against Kivy 2.3):

```bash
git clone https://github.com/ahmedfgad/CoinTex.git
cd CoinTex
python -m pip install -r requirements.txt
python main.py
```

On a machine with no audio output, start with `SDL_AUDIODRIVER=dummy python main.py`.

## Notes

- The Android APK uses the same upload certificate as CoinTex 1.4; debug and mismatched-key builds are not published. The iOS `.ipa` is unsigned, so it contains no Apple signing credentials.
- Every artifact is reproducible: `./build_desktop.sh` for Windows, macOS and Linux; `./build_android.sh` for a signed Android release; and the iOS GitHub Actions workflow.

A Python and Kivy game by Ahmed Gad.
