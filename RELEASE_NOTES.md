# CoinTex 1.4

CoinTex is a top-down arcade game written entirely in Python with [Kivy](https://kivy.org). Move your character around each level to collect all the coins before the timer runs out, while dodging monsters and fire and shooting your way through. The same Python codebase runs on Windows, macOS, Linux, Android and iPhone, and every screen and all of the graphics are drawn in code.

This release adds a new composed soundtrack, standalone desktop builds for all three desktop systems, and a round of multiplayer and interface polish.

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

- Android: on [Google Play](https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast). That is the official signed release. You can also sideload `CoinTex-android.apk` below, an unsigned debug build; turn on "install unknown apps" first.
- Windows (`CoinTex-windows.exe`): download and run. SmartScreen may warn on an unsigned app; choose "More info" then "Run anyway".
- macOS (`CoinTex-macos.zip`): unzip and open CoinTex.app. On first launch, right-click the app and choose Open to get past Gatekeeper.
- Linux (`CoinTex-linux`): run `chmod +x CoinTex-linux`, then start it. It is a single self-contained file.
- iPhone (`CoinTex-unsigned.ipa`): sideload with [AltStore](https://altstore.io) or Sideloadly, which re-sign it with your own Apple ID. See IOS_INSTALL.md.
- iPhone, Xcode (`CoinTex-xcode-project.zip`): open the project on a Mac, set your team, Archive, and run on your device or upload to the App Store.

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

- The Android `.apk` and iOS `.ipa` attached here are unsigned on purpose, so they can be built without a developer account. For the official store-signed Android app, use Google Play.
- Every artifact is reproducible: `./build_desktop.sh` for Windows, macOS and Linux; `./build_android.sh` for a signed Android release; and the iOS GitHub Actions workflow.

A Python and Kivy game by Ahmed Gad.
