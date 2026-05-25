# Android signing notes

CoinTex (`coin.tex.cointexreactfast`) was published a long time ago and the
original signing key is lost. Whether the existing app on Google Play can still
be updated depends on one setting in the Play Console. This file explains how to
check it and what to do in each case.

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

The lost key was only the upload key, so you can make a new one and ask Google to
switch to it.

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

The build script creates and reuses two private files, both ignored by git:

- `cointex-upload.keystore` is the upload key.
- `.env` holds the keystore password and alias.

Back up both of them in a safe place, such as a password manager or an encrypted
drive. Do not commit them. They are already listed in `.gitignore`.
