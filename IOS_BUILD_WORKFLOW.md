# Building the CoinTex iOS files with GitHub Actions

iOS apps must be built on a Mac. This project uses a GitHub Actions workflow to
build the app on a Mac in the cloud, so you do not need to own one. The repo is
public, so these macOS runners are free.

The workflow file is `.github/workflows/ios-build.yml`. This document explains how
to run it and where the built files appear.

## Before the first run

GitHub only runs workflows that are pushed to the repository. Commit and push the
workflow file once:

```
git add .github/workflows/ios-build.yml
git commit -m "Add iOS build workflow"
git push
```

## Run the workflow

1. Open the repository on GitHub in a web browser.
2. Click the **Actions** tab.
3. In the list on the left, click **Build iOS app**.
4. Click the **Run workflow** button on the right. Leave the branch on `master`
   and click the green **Run workflow** button.

The run starts in a few seconds and shows up in the list.

Another way to start it is to push a tag that begins with `v`, for example a tag
named `v1.3`. That starts the same build automatically.

## How long it takes

The first run takes about 45 to 90 minutes, because it builds the Python and Kivy
toolchain from source. Later runs are faster, because that toolchain is cached.

## Where the files are created

When the run finishes with a green check mark:

1. Click the finished run in the **Actions** tab.
2. Scroll to the **Artifacts** section at the bottom of the run summary page.
3. You will see two items:
   - **CoinTex-unsigned-ipa**: download it. It arrives as a zip. Unzip it to get
     `CoinTex-unsigned.ipa`. This is the file you install on an iPhone.
   - **CoinTex-xcode-project**: the Xcode project. You only need this if you later
     decide to publish the game on the App Store from a Mac.

GitHub keeps these artifacts for 30 days. After that, run the workflow again to
get fresh files.

## Install it on an iPhone

Use `CoinTex-unsigned.ipa` with the steps in `IOS_INSTALL.md`.

## If a run fails

1. Open the failed run and read the step shown in red.
2. The most common fix is the macOS version. Edit
   `.github/workflows/ios-build.yml` and change `runs-on: macos-14` to
   `runs-on: macos-13`, then run the workflow again.
3. To rebuild the toolchain from scratch, change the cache key suffix in the
   workflow from `v1` to `v2`, or delete the cache from the Actions cache list.
