# App Store screenshots

The two folders contain eight opaque, landscape PNGs each:

- `iphone/`: 2688x1242, accepted for the iPhone screenshot slot.
- `ipad/`: 2752x2064, accepted for 12.9-inch and 13-inch iPad displays.

They are reproducibly generated from the game's checked-in captures with:

```bash
python tools/make_app_store_screenshots.py
```

Before submission, compare these images with the TestFlight build on a current
iPhone and iPad. Replace any image if the shipped UI has changed.
