# CoinTex store metadata

This is the cross-platform reference for the English (United States) CoinTex
store listings. It records the live Google Play listing and the prepared Apple
App Store listing in one place so names, descriptions, privacy answers and
visual assets do not drift between releases.

Last reviewed: August 28, 2026.

The individual files under `app_store/metadata/en-US/` remain the copy-ready
source for App Store Connect. Update those files and this document together.
Google Play does not currently have an automated metadata upload directory, so
its section below is the repository snapshot of the public listing.

## Shared product identity

| Field | Value |
| --- | --- |
| App name | CoinTex |
| Android package ID | `coin.tex.cointexreactfast` |
| Apple bundle ID | `coin.tex.cointexreactfast` |
| Marketing version | `1.4.1` |
| Android version code / Apple build | `10401` |
| Developer | Ahmed Fawzy Gad |
| Price | Free |
| Ads | None |
| In-app purchases | None |
| Accounts | None |
| Primary language | English (United States), `en-US` |
| Source and marketing page | https://github.com/ahmedfgad/CoinTex |
| Canonical privacy policy | https://github.com/ahmedfgad/CoinTex/blob/master/PRIVACY.md |

## Google Play

Public listing:
https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast

These values were read from the public US English listing on August 28, 2026.
The page reported that the listing was last updated on May 29, 2026.

| Field | Published value | Length / limit |
| --- | --- | --- |
| App name | CoinTex | 7 / 30 |
| Short description | Dash through 60 arcade levels across 6 worlds — dodge monsters, fire, and time. | 79 / 80 |
| Category | Adventure | — |
| Content rating | Everyone | — |
| Developer name | Ahmed Fawzy Gad | — |
| Support email | `ahmed.f.gad@gmail.com` | — |
| Developer website | https://linkedin.com/in/ahmedfgad | — |
| Published privacy policy | https://www.freeprivacypolicy.com/live/35cbc38f-79ff-4738-a84f-9ba97b6fd0b2 | — |

The short description has one character of spare capacity. Recount it before
editing in Play Console.

### Full description

Length: 1,988 / 4,000 characters.

```text
CoinTex is a fast-paced arcade adventure across 60 hand-tuned levels and 6 themed worlds which are Meadow, Desert, Ocean, Cavern, Volcano, and Space. Every screen has the same simple mission where you need to grab every coin before the clock runs out. The hard part is staying alive long enough to do it.

Each world introduces one new twist on the same rules, shown with a quick heads-up the first time it appears:
• Meadow & Desert — learn the layout. Time your runs around wandering monsters and patrolling fires.
• Ocean — fires now pulse. Their hitbox grows and shrinks, so move on the small breaths.
• Cavern — the nearest monster locks on and chases you. You also unlock a rechargeable laser that auto-aims at your closest threat — fire, then watch the orange reload dial tick down.
• Volcano & Space — stronger hits, tighter timers, and a brutal final stretch.

Features
• 60 levels across 6 themed worlds with a steady, monotonic difficulty curve.
• An auto-aim rechargeable laser from world 4 onward, plus freeze-clock pickups that stop monsters and fires in their tracks for a few precious seconds.
• Multi-hit monsters with visible health pips, and health drops to keep you in the fight.
• Two-player local multiplayer over Wi-Fi (host or join by IP). Play co-op and share the coin count, or go head-to-head in versus mode — most coins wins.
• An interactive tutorial and a guide screen that explains every sprite, hazard, and rule in plain language.
• A built-in AI auto-player you can dial between cautious / balanced / aggressive and slow / normal / fast — let CoinTex play itself, or use it to scout a level that's giving you trouble.
• Per-world music and hand-synthesized sound effects.
• Lightweight, runs offline. No ads, no tracking, no in-app purchases.

Controls are touch-only: tap where you want to go and your character runs there, weaving past hazards on the way. From world 4, a tap on the gun button fires at the nearest monster.

Can you clear all 60 levels?
```

### Google Play visual assets

| Asset | Repository location | Notes |
| --- | --- | --- |
| App icon | `cointex_logo.png` | Ready at 512x512; the RGBA file contains only fully opaque pixels. |
| Feature graphic | `cointex_media/feature_graphic_1024x500.png` | Ready at 1024x500. |
| Phone screenshots | `cointex_media/01_menu.png` through `08_guide.png` | Eight 1280x720 landscape captures. |
| Tablet screenshots | `cointex_media/tablet_screenshots/` | Eight 1920x1080 landscape captures. |

### Next Google Play metadata update

- Replace the published FreePrivacyPolicy URL with the canonical repository
  privacy-policy URL so both stores point to the same maintained policy.
- Confirm that the release notes describe only changes in the uploaded build.
- Recheck the Data safety answers against `PRIVACY.md`: no ads, analytics,
  tracking, account, purchase or developer-server storage. Multiplayer is a
  direct connection, and the optional Host screen requests the public IP from
  `api.ipify.org` over HTTPS.
- Keep the Adventure category and Everyone rating unless the Play Console
  questionnaire produces a different result.

## Apple App Store

The App Store listing is prepared but not yet public. Copy-ready values live in
`app_store/metadata/en-US/`.

| Field | Prepared value or source | Length / limit |
| --- | --- | --- |
| Name | `app_store/metadata/en-US/name.txt`: CoinTex | 7 / 30 |
| Subtitle | `app_store/metadata/en-US/subtitle.txt`: Collect, dodge, and survive | 27 / 30 |
| Description | `app_store/metadata/en-US/description.txt` | 1,158 / 4,000 |
| Keywords | `app_store/metadata/en-US/keywords.txt` | 76 / 100 |
| Support URL | `app_store/metadata/en-US/support_url.txt` | https://github.com/ahmedfgad/CoinTex#author |
| Marketing URL | `app_store/metadata/en-US/marketing_url.txt` | https://github.com/ahmedfgad/CoinTex |
| Privacy-policy URL | `app_store/metadata/en-US/privacy_url.txt` | https://github.com/ahmedfgad/CoinTex/blob/master/PRIVACY.md |
| Review notes | `app_store/metadata/en-US/review_notes.txt` | 802 characters |
| Promotional text | Not set | Optional, up to 170 characters |
| Primary category | Games | — |
| Primary subcategory | Action | — |
| Suggested secondary category | Casual | — |
| SKU | `cointex-ios-001` | Internal; confirm when creating the record |
| Copyright | Not set | Enter the account holder's legal copyright value |

### Subtitle

```text
Collect, dodge, and survive
```

### Keywords

```text
arcade,collector,offline,multiplayer,autoplay,retro,casual,action,maze,coins
```

### Description

```text
Collect every coin before time runs out in a colorful arcade challenge built for quick play and deeper mastery.

Explore six worlds and 60 handcrafted levels. Each world introduces faster enemies, moving and pulsing hazards, tougher monsters, freeze clocks, and new tactical decisions. Move with a tap, dodge danger, and use the auto-aiming blaster when a monster gets too close.

Features:

• 6 worlds and 60 levels
• Responsive tap-to-move controls
• Monsters, fire hazards, freeze clocks, and an auto-aiming blaster
• Up to three stars per level based on remaining health
• A built-in tutorial and illustrated game guide
• An Auto Player that can take over and demonstrate each level
• Optional two-player Co-op and Versus modes over a direct network connection
• Progress and settings stored on your device
• No ads, analytics, tracking, accounts, or in-app purchases

In Co-op, work together to clear the arena. In Versus, race for the same coins and finish with the higher score. Nearby play works over the same Wi-Fi; advanced players can also connect directly over the internet.

Every screen and game character is drawn in code with Python and Kivy.
```

### App Store review notes

```text
CoinTex requires no account, login, purchase, or external hardware. The complete single-player game, tutorial, guide, and Auto Player can be reviewed offline.

The app is landscape-only and supports iPhone and iPad. To see the privacy policy, open About from the main menu and tap Privacy Policy.

Multiplayer is optional and requires a second CoinTex device. Choosing Host Game requests Local Network permission, opens a direct peer-to-peer listener, and shows a same-Wi-Fi address. The screen also retrieves the host's public IPv4 address from api.ipify.org over verified HTTPS for optional advanced internet play. No developer server routes or stores gameplay messages.

The Auto button is not a paid or online AI service. It is a deterministic, on-device game-playing algorithm included in the app.
```

### App Store product settings

- Universal iPhone and iPad app, landscape-only, minimum iOS 15.
- Price: free.
- App Privacy: no data collected and no tracking.
- Export compliance: standard/exempt HTTPS only;
  `ITSAppUsesNonExemptEncryption` is `false`.
- Age-rating questionnaire: disclose infrequent or mild cartoon/fantasy
  violence because monsters can be shot without blood or gore. Record the
  rating generated by App Store Connect; do not guess it here.
- Do not select Made for Kids unless all present and future content follows
  Apple's Kids Category requirements.

### App Store visual assets

| Slot | Repository location | Count and dimensions |
| --- | --- | --- |
| App icon source | `cointex_logo.png` | 512x512 opaque source; the workflow generates the complete opaque iPhone/iPad catalog and 1024x1024 marketing icon. |
| iPhone screenshots | `app_store/screenshots/iphone/` | Eight 2688x1242 landscape PNGs. |
| 12.9-inch/13-inch iPad screenshots | `app_store/screenshots/ipad/` | Eight 2752x2064 landscape PNGs. |
| App previews | Not prepared | Optional; up to three per device class. |

Upload screenshots in filename order: menu, world map, level selection,
gameplay, combat/chasers, win/stars, Auto Player, and Guide.

## Release checklist

Before changing either production listing:

1. Confirm the app version/build identifiers in this document match the
   uploaded APK/AAB or IPA.
2. Recheck every character count after editing copy.
3. Verify screenshots against the exact production or TestFlight build.
4. Confirm support and privacy URLs are publicly reachable while signed out.
5. Recheck privacy, Data safety, export-compliance and age-rating answers when
   networking, analytics, ads, purchases, accounts or third-party services
   change.
6. Keep credentials, keystores, certificates, API keys and provisioning
   profiles out of metadata and Git.

Current official references:

- Google Play listing requirements: https://support.google.com/googleplay/android-developer/answer/9859152
- Google Play preview assets: https://support.google.com/googleplay/android-developer/answer/1078870
- Apple platform-version metadata: https://developer.apple.com/help/app-store-connect/reference/platform-version-information
- Apple screenshot specifications: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications
- CoinTex App Store submission steps: `APP_STORE_SUBMISSION.md`
