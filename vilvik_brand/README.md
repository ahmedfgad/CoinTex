# Vilvik intro / outro bumpers

Reusable animated Vilvik logo bumpers for Vilvik videos. The logo uses the real
website "draw-on" choreography (each of the 6 mark parts is stroke-traced, then
the fill reveals), on a dark navy backdrop with the `vilvik.com` wordmark, then a
gentle breathing glow. Each card is 4.5s and fades in from / out to black.

## Files

| File | What it is |
| --- | --- |
| `vilvik_intro_4k.mp4` | Intro bumper, 3840×2160 / 60fps, H.264 + AAC stereo |
| `vilvik_outro_4k.mp4` | Outro bumper, 3840×2160 / 60fps |
| `vilvik_intro_1080p.mp4` | Intro bumper, 1920×1080 / 60fps |
| `vilvik_outro_1080p.mp4` | Outro bumper, 1920×1080 / 60fps |
| `vilvik_intro.wav` | Intro soundtrack — rising whoosh + chime as the logo completes (mono 44.1k) |
| `vilvik_outro.wav` | Outro soundtrack — soft chime + low pad (mono 44.1k) |
| `make_vilvik_cards.py` | Self-contained script that regenerates everything |
| `vilvik_logo_animated.svg` | The 6-part Vilvik mark (with stroke clones for the draw-on) |
| `draw-on.css` | The exact website draw-on keyframes/timing |

The intro and outro share the **same animated visuals**; only the audio differs.

## Use them

Drop a card before/after a clip. With the bundled static ffmpeg
(`python -c "import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())"`), to bookend
a 1080p/60 video whose codec matches the cards, stream-copy concat:

```bash
printf "file 'vilvik_intro_1080p.mp4'\nfile 'myvideo.mp4'\nfile 'vilvik_outro_1080p.mp4'\n" > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4
```

If your video's codec/params differ, re-encode on concat instead (concat filter),
or render the cards to match your video's resolution/fps first (see below).

## Re-create / re-render

Requirements (already set up on the build machine):
- Python with `numpy`, `Pillow`, `imageio-ffmpeg` (provides a static ffmpeg — no system ffmpeg needed).
- A headless Chrome/Chromium for deterministic frame rendering. The script defaults
  to Playwright's `chrome-headless-shell`; override with the `CHROME_SHELL` env var:
  `CHROME_SHELL=/path/to/chrome-headless-shell python make_vilvik_cards.py`.

```bash
python make_vilvik_cards.py                 # both cards, 1080p / 60fps
python make_vilvik_cards.py --res 4k        # both cards, 3840×2160 / 60fps
python make_vilvik_cards.py --which intro --width 1920 --height 1080 --fps 30
```

Outputs `vilvik_<intro|outro>_<res>.mp4` and the matching `.wav` next to the script.
The layout scales with the chosen height, so any resolution stays crisp (the logo
is vector). How it works: `make_vilvik_cards.py` builds an HTML card that inlines
`vilvik_logo_animated.svg` + `draw-on.css`, renders each frame deterministically by
freezing the CSS animation clock at that frame's timestamp (`?t=` + the Web
Animations API) and screenshotting with headless Chrome, synthesizes the audio
with NumPy, and encodes with ffmpeg.

## Tweaks

- **Timing / colors / glow:** edit `card_html()` in `make_vilvik_cards.py`.
- **Animation style:** `draw-on.css` is the website's default. The site also has
  cascade / scatter / spiral / color-wave / origami variants in the Vilvik repo
  (`pygadproject/assets/css/logo-animations/`) — swap the CSS + the wrapper class
  (`vlogo-anim--draw-on`) to use another.
- **Audio:** edit `make_intro_audio()` / `make_outro_audio()` (pure NumPy synthesis).
