# App Store screenshots

`iphone_6_9/` contains opaque 2796x1290 landscape PNGs, an accepted size for
Apple's 6.9-inch iPhone screenshot slot. They are reproducibly generated from
the game's checked-in captures with:

```bash
python tools/make_app_store_screenshots.py
```

Before submission, compare these images with the TestFlight build on a current
iPhone. Replace any image if the shipped UI has changed.
