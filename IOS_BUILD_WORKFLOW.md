# Building CoinTex for iPhone

CoinTex has two separate GitHub Actions workflows:

- **Build iOS app** creates a validated unsigned Release IPA and a portable
  Xcode project. It uses no Apple account and is safe to run for ordinary
  release testing.
- **Build signed iOS App Store app** creates the distribution-signed archive
  and IPA, validates the signing/profile, and can upload to App Store Connect.
  It is manual and requires the protected Apple credentials documented in
  [APP_STORE_SUBMISSION.md](APP_STORE_SUBMISSION.md).

Both run on a macOS 26 runner and fail unless Xcode 26 with the iOS 26 SDK is
active. Apple has required iOS uploads to use that SDK generation since April
28, 2026.

## Version and app identity

The single source of truth is `ios/CoinTex.xcconfig`:

- Bundle ID: `coin.tex.cointexreactfast`
- Marketing version: `1.4.1`
- Build number: `10401`
- Minimum version: iOS 15
- Device family: iPhone

Every replacement uploaded to App Store Connect needs a new
`CURRENT_PROJECT_VERSION`. Do not change the bundle ID after creating the
Apple App ID/App Store Connect record.

## Run the unsigned build

1. Push the changes to GitHub.
2. Open the repository's **Actions** tab.
3. Select **Build iOS app** and choose **Run workflow**.
4. Wait for the Python/Kivy toolchain and Release app to finish.
5. Download the artifacts from the completed run:
   - `CoinTex-unsigned-ipa`: for AltStore/Sideloadly testing only. See
     [IOS_INSTALL.md](IOS_INSTALL.md).
   - `CoinTex-xcode-project`: a portable project with clean runtime source,
     icons, launch screen, version/bundle settings, privacy manifest, and
     transport/privacy declarations already applied.

The first run can take 45 to 120 minutes because Python and Kivy compile from
source. Later runs reuse a cache keyed to the pinned iOS requirements and SDK
generation.

Before artifacts are uploaded, the workflow verifies:

- iOS 26 SDK and arm64 executable;
- iPhone-only device family and iOS 15 deployment target;
- bundle ID, marketing version, and build number;
- opaque compiled app-icon catalog and launch storyboard;
- Local Network purpose text and exempt-encryption declaration;
- App Privacy manifest at the app-bundle root;
- no arbitrary App Transport Security bypass.

## Build locally on a Mac

Install full Xcode 26 with the iOS 26 SDK, select it with `xcode-select`, and
install Homebrew. Then run:

```bash
./build_ios.sh
```

The script installs pinned build dependencies in `.ios-venv`, builds the
kivy-ios distribution, and creates `cointex-ios/cointex.xcodeproj`. It does
not sign or upload the app.

Open the project, select your Apple Developer team under **Signing &
Capabilities**, and run the Release app on a real iPhone. For the App Store,
archive and distribute it through Organizer, or use the protected signed
workflow.

## Signed App Store build

Do not put Apple files in the repository. Complete the developer-account,
certificate/profile, GitHub environment, TestFlight, and product-page steps in
[APP_STORE_SUBMISSION.md](APP_STORE_SUBMISSION.md).

The signed workflow has an `upload_to_app_store_connect` switch:

- Disabled: create and locally validate the signed App Store IPA without
  contacting Apple.
- Enabled: additionally authenticate with the App Store Connect API, validate
  the IPA with Apple, and upload it for TestFlight processing.

Normal public releases never call this signed workflow.

## Troubleshooting

- Do not downgrade the runner to macOS 13/14 or Xcode 16; those SDKs no longer
  satisfy current App Store submission requirements.
- If a cached toolchain becomes inconsistent, change the cache-key suffix in
  both iOS workflows or remove that cache in GitHub Actions settings.
- If the signed workflow says the profile is wrong, recreate an **App Store
  Connect** distribution profile for the exact bundle ID. Development and
  ad-hoc profiles are rejected intentionally.
- If Apple rejects a reused build number, increment
  `CURRENT_PROJECT_VERSION` in `ios/CoinTex.xcconfig` and build again.
- A successful compile is not the end of release testing. Use the exact
  uploaded build in TestFlight on a real iPhone before submission.
