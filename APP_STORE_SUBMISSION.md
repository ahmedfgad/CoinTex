# Publishing CoinTex on Apple's App Store

The repository is configured for an iPhone App Store release with bundle ID
`coin.tex.cointexreactfast`, marketing version `1.4.1`, build `10401`, minimum
iOS 15, and the iOS 26 SDK. Release identity and version values live in
[`ios/CoinTex.xcconfig`](ios/CoinTex.xcconfig).

No certificate, provisioning profile, API key, or password belongs in Git.

## What the repository now provides

- A clean, portable kivy-ios Xcode project and unsigned test IPA from
  `.github/workflows/ios-build.yml`.
- A manual, credential-gated signed archive/export/upload pipeline in
  `.github/workflows/ios-app-store.yml`.
- App Store metadata in `app_store/metadata/en-US/` and 2796x1290 iPhone
  screenshots in `app_store/screenshots/iphone_6_9/`.
- An opaque 1024px App Store icon, launch storyboard, landscape orientations,
  Local Network purpose text, export-compliance declaration, and privacy
  manifest generated into the Xcode project.
- An in-app Privacy Policy screen and the public policy in `PRIVACY.md`.
- Local validation of the SDK, bundle/version, arm64 executable, device family,
  asset catalog, privacy manifest, provisioning profile, and code signature.

Apple account setup, a real-device/TestFlight test, and App Store review are
external steps and cannot be completed before the developer membership exists.

## 1. Create the Apple records

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/enroll/)
   and accept the current agreements.
2. In Certificates, Identifiers & Profiles, register an explicit App ID using
   `coin.tex.cointexreactfast`. Confirm this identifier before the first upload;
   App Store Connect associates uploaded builds by bundle ID and it cannot be
   changed for that app record later.
3. Create an **Apple Distribution** certificate and export it from Keychain as
   a password-protected `.p12` file.
4. Create an **App Store Connect** distribution provisioning profile for that
   exact App ID and download the `.mobileprovision` file.
5. In [App Store Connect](https://appstoreconnect.apple.com/), create the iOS app
   record. Select the same bundle ID. A practical SKU is `cointex-ios-001`.
6. If automated upload will be used, create an App Store Connect API key with
   access to upload builds. Download its `.p8` file immediately; Apple only
   offers that private key once.

## 2. Protect the signing credentials in GitHub

Create a GitHub Actions environment named `app-store`. Add a required reviewer
if the repository has more than one administrator, then add these environment
secrets:

| Secret | Value |
| --- | --- |
| `IOS_DISTRIBUTION_CERTIFICATE_BASE64` | Base64 of the Apple Distribution `.p12` |
| `IOS_DISTRIBUTION_CERTIFICATE_PASSWORD` | Password used when exporting the `.p12` |
| `IOS_APP_STORE_PROVISIONING_PROFILE_BASE64` | Base64 of the App Store `.mobileprovision` |
| `IOS_TEAM_ID` | The 10-character Apple Developer Team ID |
| `APP_STORE_CONNECT_API_KEY_ID` | API key ID; needed only for automated upload |
| `APP_STORE_CONNECT_API_ISSUER_ID` | API issuer ID; needed only for automated upload |
| `APP_STORE_CONNECT_API_PRIVATE_KEY_BASE64` | Base64 of `AuthKey_<ID>.p8`; needed only for upload |

On macOS or Linux, create a one-line Base64 value without modifying the source
file:

```bash
openssl base64 -A -in distribution.p12
openssl base64 -A -in CoinTex_AppStore.mobileprovision
openssl base64 -A -in AuthKey_EXAMPLE.p8
```

The workflow verifies that the profile is unexpired, is not a development or
ad-hoc profile, belongs to the configured Team ID, and matches the bundle ID.

## 3. Build, test, and upload

1. Run **Build iOS app** first. It uses no secrets and proves that the current
   source builds with Xcode/iOS SDK 26. Download the portable Xcode project if
   you want to run it directly from Xcode.
2. Test the Release app on at least one real iPhone. Exercise first launch,
   audio, saving/resetting progress, landscape rotation, tutorial, gameplay,
   background/foreground transitions, and the Local Network allow/deny paths.
3. Run **Build signed iOS App Store app** with upload disabled. This exports the
   signed IPA but does not contact App Store Connect.
4. After the App Store Connect app record exists, run it again with
   `upload_to_app_store_connect` enabled. The workflow validates the IPA with
   Apple and uploads it. Wait for App Store Connect processing, then distribute
   it to internal TestFlight testers.
5. Complete a TestFlight pass on the exact uploaded build before selecting it
   for review. Increment `CURRENT_PROJECT_VERSION` for every replacement upload,
   even if the marketing version remains `1.4.1`.

## 4. Complete the product page

Copy the prepared English metadata and screenshots from `app_store/`. Suggested
App Store choices are:

- Primary category: **Games**; subcategory: **Action**. A reasonable secondary
  category is **Casual**.
- Price: free, matching the app's lack of purchases.
- App Privacy: no data collected or used for tracking. The public-IP request is
  made only when Host Game is opened; ipify states that visitor information is
  not logged. Recheck the service policy when submitting.
- Export compliance: the app uses standard/exempt HTTPS and no proprietary or
  non-exempt cryptography. `ITSAppUsesNonExemptEncryption` is set to `false`.
- Age rating: disclose infrequent/mild cartoon or fantasy violence (monsters
  can be shot, with no blood or gore) and answer all other questionnaire items
  according to the current build. Do not select **Made for Kids** unless every
  future version will follow Apple's Kids Category rules.
- Review notes: use `app_store/metadata/en-US/review_notes.txt`; no demo account
  is required.

The privacy policy and support URLs must be publicly reachable before review.
Push `PRIVACY.md` to the `master` branch before entering its URL in App Store
Connect.

One non-code content-rights check remains for the account holder: the melodies
are repository-authored, but the current WAVs were rendered through the machine's
default General MIDI SoundFont. Keep proof that the specific SoundFont permits
commercial App Store distribution before answering Apple's content-rights
question. If that provenance cannot be recovered, rerender the tracks with a
SoundFont whose license is documented.

## Mac availability

This release targets iPhone, not iPad or Mac Catalyst. App Store Connect can
still offer the unmodified iPhone app to users of Apple-silicon Macs. In
**Pricing and Availability > iPhone and iPad Apps on Apple Silicon Mac**, leave
**Make this app available** selected only after testing the TestFlight build on
an Apple-silicon Mac. That version is the iPhone app running in Apple's
compatibility environment; it is not a native macOS app and will not support
Intel Macs.

The repository's PyInstaller `CoinTex.app` is a separate native desktop build.
Publishing that as a macOS App Store platform would require a separate Xcode
packaging/signing sandbox-entitlement effort. It is not included in this iPhone
submission.

## Current Apple requirements used here

- [Upcoming submission requirements](https://developer.apple.com/news/upcoming-requirements/)
- [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds)
- [Manage app privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/)
- [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/)
- [iPhone and iPad apps on Apple-silicon Macs](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/manage-availability-of-iphone-and-ipad-apps-on-macs-with-apple-silicon)
