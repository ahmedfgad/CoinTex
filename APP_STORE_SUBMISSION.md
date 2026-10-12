# Publishing CoinTex on Apple's App Store

The repository is configured for a universal iPhone and iPad App Store release with bundle ID
`coin.tex.cointexreactfast`, marketing version `1.4.2`, build `10403`, minimum
iOS 15, and the iOS 26 SDK. Release identity and version values live in
[`ios/CoinTex.xcconfig`](ios/CoinTex.xcconfig).

No certificate, provisioning profile, API key, or password belongs in Git.

## Keep release credentials for future updates

Create a password-manager record named **CoinTex App Store release** and store
the Apple Team ID, API key ID and issuer ID there. Back up the Apple
Distribution `.p12` and its password, the App Store provisioning profile, and
the API private-key `.p8` in encrypted storage with that record. Apple offers
the `.p8` private key only once. Keep the certificate and profile expiration
dates and the GitHub repository's `app-store` environment name with the record.
Add the values to GitHub Actions environment secrets only; never commit them or
put them in a release artifact. The app identity and future build-number source
remain in `ios/CoinTex.xcconfig`.

## What the repository now provides

- A clean, portable kivy-ios Xcode project and unsigned test IPA from
  `.github/workflows/ios-build.yml`.
- A manual, credential-gated signed archive/export/upload pipeline in
  `.github/workflows/ios-app-store.yml`.
- App Store metadata in `app_store/metadata/en-US/`, 2688x1242 iPhone
  screenshots in `app_store/screenshots/iphone/`, and 2752x2064 iPad
  screenshots in `app_store/screenshots/ipad/`.
- An opaque 1024px App Store icon, launch storyboard, landscape orientations,
  Local Network purpose text, export-compliance declaration, and privacy
  manifest generated into the Xcode project.
- An in-app Privacy Policy screen and the public policy in `PRIVACY.md`.
- iPhone/iPad left-edge swipe-right Back navigation on menu and tutorial
  screens. Android accepts inward swipes from either edge. Visible Back buttons
  remain available on both platforms.
- Local validation of the SDK, bundle/version, arm64 executable, device family,
  asset catalog, privacy manifest, provisioning profile, and code signature.

The App Store Connect record and product page are prepared. Build `10402` was
rejected by Apple's automated upload scan for a missing camera purpose string.
The bundled framework includes optional camera APIs, although CoinTex does not
use the camera. Build `10403` adds a clear purpose string and was uploaded
successfully on 2026-10-12, completed processing, and was submitted for App
Review. App Store Connect reports **Waiting for Review**. Automatic release
after approval is selected. The App Privacy disclosure is published, App Review
contact details are saved, the account is identified as a non-trader, and
France is excluded.

## 1. Apple records already created

The App Store Connect record is permanent. Keep these identifiers for updates:

- Apple Developer Team ID: `Y4Q9DBXM59`.
- Explicit App ID / bundle ID: `coin.tex.cointexreactfast`.
- App Store Connect Apple ID: `6822005164`; SKU: `cointex-ios-001`.
- Version: `1.4.2`, uploaded build `10403` (build `10402` was rejected).
- Distribution: public and free in 174 countries and regions. France is
  excluded for launch; see the encryption note below.
- Age rating: 13+ from the completed questionnaire.
- Product-page screenshots: eight iPhone and eight iPad images.
- Apple Distribution certificate `AD9Z7N6FD4` expires 2027-08-28. The shared
  certificate and App Store Connect API private key are already stored outside
  Git under `C:\Users\ahmed\OneDrive\Secrets\apple-signing`; the API key ID is
  `75FGUDQCLQ`. The API issuer ID is visible in App Store Connect > Users and
  Access > Integrations > App Store Connect API.
- CoinTex App Store profile `RJYZ59GLHP` (`CoinTex App Store Distribution`)
  was created for this App ID and certificate and expires 2027-08-28.

## 2. Apple signing credentials

1. Use the existing Apple Distribution certificate and App Store Connect API
   key in `C:\Users\ahmed\OneDrive\Secrets\apple-signing`. Do not create
   duplicates or commit their private files.
2. The `CoinTex App Store Distribution` profile is downloaded locally and is
   app-specific. It expires 2027-08-28.
3. Protect these files and their passwords in encrypted storage for future
   updates. The `.p8` file can only be downloaded once from Apple.

## 3. Protect the signing credentials in GitHub

The GitHub Actions environment `app-store` and its signing secrets are already
configured. Keep these exact names when rotating or restoring them:

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

## 4. Build, test, and upload

1. Run **Build iOS app** first. It uses no secrets and proves that the current
   source builds with Xcode/iOS SDK 26. Download the portable Xcode project if
   you want to run it directly from Xcode.
2. Test the Release app on at least one real iPhone and one real iPad. Exercise first launch,
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
   even if the marketing version remains `1.4.2`.

## 5. Complete and submit the product page

Copy the prepared English metadata and screenshots from `app_store/`. The
cross-store reference and copy-ready values are summarized in
[`STORE_METADATA.md`](STORE_METADATA.md). Suggested App Store choices are:

- Primary category: **Games**; subcategory: **Action**. A reasonable secondary
  category is **Casual**.
- Price: free, matching the app's lack of purchases.
- App Privacy: no data collected or used for tracking. The public-IP request is
  made only when Host Game is opened; ipify states that visitor information is
  not logged. Recheck the service policy when submitting.
- Export compliance: the optional public-IP lookup uses Python's TLS/SSL
  implementation for HTTPS to `api.ipify.org`. France is excluded from the
  initial 174-region release because Apple requires a French encryption
  declaration for standard encryption implemented outside Apple's operating
  system when distributing in France. Keep `ITSAppUsesNonExemptEncryption`
  aligned with Apple's export-compliance questionnaire and the final bundle.
- Age rating: the saved questionnaire yields **13+**, including frequent
  fantasy/cartoon violence and weapons and infrequent optional contests. Review
  each response against the submitted build. Do not select **Made for Kids**
  unless every future version will follow Apple's Kids Category rules.
- Review notes: use `app_store/metadata/en-US/review_notes.txt`; no demo account
  is required.

The privacy policy and support URLs must be publicly reachable before review.
Push `PRIVACY.md` to the `master` branch before entering its URL in App Store
Connect.

The compositions are owner-authored. All seven shipped WAVs have now been
rerendered from the explicit FluidR3 GM SoundFont using the documented Linux
package, rather than the machine-dependent `default-GM.sf2` alias. The MIT
copyright and license are included in the About screen and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The App Store content-rights
response is saved as “Yes, this app has the necessary rights to its third-party
content.”

The App Review contact name, public developer email, and international-format
phone number are saved.

The account holder identified as a non-trader under the Digital Services Act.

The `app-store` GitHub Actions environment contains the required signing and
App Store Connect API secrets. Keep their source files in encrypted backups;
never commit them. `UIRequiresFullScreen` is enabled for the landscape-only iPad
game so it does not advertise iPad multitasking layouts it cannot render.

## Android update

The iPhone-style edge-back navigation is also enabled on Android. This is an
update to the existing Google Play app, not a new listing: package ID stays
`coin.tex.cointexreactfast`, and buildozer numeric version code is `10402`.
The unsigned Android CI build passed. The signed release workflow reads the
existing Play upload key from the protected `google-play` GitHub Actions
environment and verifies its certificate fingerprint. It normalizes the
existing key to a standard PKCS#12 store for Android bundle signing. The signed
build `10402` (version `1.4.2`) was submitted to Google Play production review
on 2026-10-12. Google reports missing deobfuscation and native debug symbols as
warnings; they do not block this release. Managed publishing is off, so Google
will roll it out after review approval.

## Mac availability

This release targets iPhone and iPad, but not Mac Catalyst. App Store Connect can
also offer the unmodified iOS app to users of Apple-silicon Macs. In
**Pricing and Availability > iPhone and iPad Apps on Apple Silicon Mac**, keep
**Make this app available** turned off until the TestFlight build is tested on
an Apple-silicon Mac. That version is the iPhone/iPad app running in Apple's
compatibility environment; it is not a native macOS app and will not support
Intel Macs.

The repository's PyInstaller `CoinTex.app` is a separate native desktop build.
Publishing that as a macOS App Store platform would require a separate Xcode
packaging/signing sandbox-entitlement effort. It is not included in this iOS
submission.

## Current Apple requirements used here

- [Upcoming submission requirements](https://developer.apple.com/news/upcoming-requirements/)
- [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds)
- [Manage app privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/)
- [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/)
- [iPhone and iPad apps on Apple-silicon Macs](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/manage-availability-of-iphone-and-ipad-apps-on-macs-with-apple-silicon)
