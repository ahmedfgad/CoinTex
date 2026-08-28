# Android signing notes

This document covers Android signing. Apple signing uses unrelated Apple
certificates and provisioning profiles; see [APP_STORE_SUBMISSION.md](APP_STORE_SUBMISSION.md).

CoinTex (`coin.tex.cointexreactfast`) uses Google Play App Signing. Its upload
key is kept outside this public repository and referenced by the private `.env`
file. This document records the expected certificate and the recovery options
if that key becomes unavailable.

Google Play currently expects the upload certificate with SHA-1 fingerprint
`C6:81:B6:85:58:91:82:C4:5C:72:F6:95:71:67:A3:E8:75:AF:63:39`. The public
CoinTex 1.4 APK and current release key use that certificate. The matching
private key is deliberately not in this repository. `build_android.sh` verifies
the fingerprint before starting a release build and refuses to create an AAB
with a different key.

## Step 1: check if the app uses Play App Signing

1. Open the Play Console and select CoinTex.
2. Go to Test and release > Setup > App integrity (older menus call it App signing).
3. Look at the App signing key section.

There are two possible cases:

- The page shows an app signing key certificate managed by Google. This means
  Play App Signing is on. Google holds the real signing key, and the key you lost
  was only the upload key, which can be replaced. Go to Step 2A.
- The page says the app is not enrolled, or that you manage signing yourself, and
  no Google key is shown. This means you sign the app yourself. Go to Step 2B.

## Step 2A: Play App Signing is on

If the upload key is lost, you can make a new one and ask Google to switch to it.

1. Create the new upload key and its certificate:

       ./build_android.sh

   The first run creates `cointex-upload.keystore` and `upload_certificate.pem`.

2. In the Play Console open App integrity, find the upload key section, and choose
   to reset the upload key. If you do not see the option, use Help > Contact
   support and ask to reset the upload key.

3. Upload the `upload_certificate.pem` file.

4. Wait for Google to apply the change. This usually takes a day or two.

5. From then on sign every upload with `cointex-upload.keystore`. The build script
   already does this. Upload the .aab from the bin folder as a new release. It
   stays the same app, same listing, same users.

6. Replace `EXPECTED_UPLOAD_SHA1` in `build_android.sh` with the SHA-1 shown for
   the new upload certificate in Play Console. Do this only after Google has
   confirmed the reset.

The app signing key held by Google does not change, so people who already have the
app keep getting updates as normal.

## Step 2B: you sign the app yourself and the key is lost

If the app was never enrolled in Play App Signing and the keystore is gone, Google
cannot reset it. Nobody can. Enrolling now would need the original key, which is
lost too.

The only option is to publish a new app with a new application id:

1. Change the id in `buildozer.spec`, for example:

       package.name = cointexreactfast2
       package.domain = coin.tex

   This gives the id `coin.tex.cointexreactfast2`.

2. Build with a new keystore (the build script makes one) and turn on Play App
   Signing for the new app during its first release, so this cannot happen again.

3. Create a new store listing. The old listing stays up but you cannot update it.
   Current users keep the old version until they install the new app.

Before doing this, check Step 1 again. Most apps published through the Play Console
in recent years use Play App Signing, which puts you in the easier Step 2A case.

## Keep your keys safe

The build script uses two private files, both ignored by git:

- `cointex-upload.keystore` is the default upload-key location. Set
  `KEYSTORE_PATH` in `.env` when the key is stored elsewhere.
- `.env` holds the keystore password, alias and optional key path.

Back up both of them in a safe place, such as a password manager or an encrypted
drive. Do not commit them. They are already listed in `.gitignore`.
