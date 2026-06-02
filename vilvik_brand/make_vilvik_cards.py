"""Re-create the Vilvik intro and outro bumper cards (video + audio).

Self-contained: renders the animated Vilvik "draw-on" logo (the real website
choreography, from the bundled vilvik_logo_animated.svg + draw-on.css) on a dark
navy backdrop with the `vilvik.com` wordmark, deterministically frame-by-frame
via headless Chrome, then synthesizes the audio with NumPy and encodes mp4s.

  intro: rising whoosh + chime as the logo completes
  outro: soft chime + low pad, fading to black

Usage:
  python make_vilvik_cards.py                 # both, 1080p/60
  python make_vilvik_cards.py --res 4k        # both, 3840x2160/60
  python make_vilvik_cards.py --which intro --width 1920 --height 1080 --fps 30

Requirements (already present on the build machine):
  - Python with numpy + Pillow + imageio-ffmpeg (provides a static ffmpeg)
  - A headless Chrome/Chromium. Set CHROME_SHELL env var to its path, or rely on
    the default below (Playwright's chrome-headless-shell).
"""

import argparse
import os
import subprocess
import sys
import wave
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CHS = os.environ.get(
    "CHROME_SHELL",
    os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-1223/"
                       "chrome-headless-shell-linux64/chrome-headless-shell"))

CARD_SECONDS = 4.5
SR = 44100
WORKERS = 6


# --------------------------------------------------------------------------- #
# Card HTML (dark navy + draw-on logo + vilvik.com), scaled to the resolution.
# --------------------------------------------------------------------------- #
def card_html(svg, drawon_css, W, H):
    s = H / 1080.0
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#070c18}}
.bg{{position:fixed;inset:0;background:
  radial-gradient(ellipse 72% 70% at 50% 44%, #16243f 0%, #0d1730 46%, #070c18 100%);}}
.stage{{position:fixed;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;}}
.content{{display:flex;flex-direction:column;align-items:center;gap:{54*s:.1f}px;
  animation:card-in .55s ease-out both;}}
@keyframes card-in{{0%{{opacity:0;transform:scale(.985)}}100%{{opacity:1;transform:scale(1)}}}}
.logo-wrap{{width:{460*s:.1f}px;height:{389*s:.1f}px;
  animation:breathe 4.5s ease-in-out infinite 2.6s;}}
@keyframes breathe{{0%,100%{{filter:drop-shadow(0 0 {16*s:.1f}px rgba(37,99,235,.10))}}
  50%{{filter:drop-shadow(0 0 {36*s:.1f}px rgba(37,99,235,.42))}}}}
.vlogo-anim{{width:100%;height:100%;display:block;line-height:0}}
.vlogo-anim svg{{display:block;overflow:visible;width:100%;height:100%}}
.wordmark{{font-family:'DejaVu Sans','Liberation Sans',sans-serif;font-weight:300;
  font-size:{42*s:.1f}px;letter-spacing:.46em;color:#eaf1ff;text-indent:.46em;
  opacity:0;animation:word-in .85s ease-out both 1.85s;}}
@keyframes word-in{{0%{{opacity:0;transform:translateY({12*s:.1f}px)}}
  100%{{opacity:1;transform:translateY(0)}}}}
.blackout{{position:fixed;inset:0;background:#000;pointer-events:none;
  animation:blackout {CARD_SECONDS}s linear both;}}
@keyframes blackout{{0%{{opacity:1}}9%{{opacity:0}}90%{{opacity:0}}100%{{opacity:1}}}}
{drawon_css}
</style></head>
<body>
  <div class="bg"></div>
  <div class="stage"><div class="content">
    <div class="logo-wrap">
      <div class="vlogo-anim vlogo-anim--once vlogo-anim--color vlogo-anim--draw-on">
        {svg}
      </div>
    </div>
    <div class="wordmark">vilvik.com</div>
  </div></div>
  <div class="blackout"></div>
  <script>
    const T = parseFloat(new URLSearchParams(location.search).get('t') || '0');
    function freeze(){{document.getAnimations().forEach(a=>{{a.pause();a.currentTime=T;}});}}
    freeze(); requestAnimationFrame(()=>{{freeze();requestAnimationFrame(freeze);}});
  </script>
</body></html>"""


# --------------------------------------------------------------------------- #
# Deterministic frame rendering with headless Chrome (?t= freezes the clock).
# --------------------------------------------------------------------------- #
_ctx = {}


def _init_worker(profiles_base, W, H):
    _ctx["profile"] = os.path.join(profiles_base, "p%d" % os.getpid())
    _ctx["W"], _ctx["H"] = W, H
    os.makedirs(_ctx["profile"], exist_ok=True)


def _render_frame(task):
    html_path, out_png, t_ms = task
    cmd = [CHS, "--no-sandbox", "--user-data-dir=" + _ctx["profile"],
           "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
           "--disable-gpu", "--window-size=%d,%d" % (_ctx["W"], _ctx["H"]),
           "--force-device-scale-factor=1", "--virtual-time-budget=700",
           "--run-all-compositor-stages-before-draw",
           "--screenshot=" + out_png, "file://%s?t=%.3f" % (html_path, t_ms)]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
    if r.returncode != 0 or not os.path.exists(out_png):
        raise RuntimeError("render failed t=%s" % t_ms)
    return out_png


def render_frames(html_text, work, W, H, fps):
    html_path = os.path.join(work, "card.html")
    open(html_path, "w").write(html_text)
    frames = os.path.join(work, "frames")
    os.makedirs(frames, exist_ok=True)
    n = int(round(CARD_SECONDS * fps))
    tasks = [(html_path, os.path.join(frames, "f_%05d.png" % i), (i / fps) * 1000.0)
             for i in range(n)]
    profiles = os.path.join(work, "profiles")
    os.makedirs(profiles, exist_ok=True)
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=_init_worker,
                             initargs=(profiles, W, H)) as ex:
        list(ex.map(_render_frame, tasks))
    return frames


# --------------------------------------------------------------------------- #
# Audio (NumPy) -> wav
# --------------------------------------------------------------------------- #
def _bell(t, f0, dur, amp):
    env = np.exp(-t / (dur * 0.32)) * (t >= 0)
    sig = np.zeros_like(t)
    for ratio, a in [(1.0, 1.0), (2.76, 0.55), (5.40, 0.32), (8.93, 0.18)]:
        sig += a * np.sin(2 * np.pi * f0 * ratio * t)
    return amp * env * sig


def _whoosh(t, dur):
    n = len(t)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    prev = 0.0
    for i in range(n):
        frac = min(i / (dur * SR), 1.0)
        a = 0.0025 + 0.05 * frac
        prev = prev + a * (noise[i] - prev)
        out[i] = prev
    swell = np.clip(t / 1.6, 0, 1) ** 1.4
    fall = np.exp(-np.clip(t - 1.7, 0, None) / 0.9)
    return out * swell * fall * 9.0


def _write_wav(path, mono):
    pcm = (np.clip(mono, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def make_intro_audio(path):
    n = int(CARD_SECONDS * SR); t = np.arange(n) / SR
    sig = _whoosh(t, CARD_SECONDS) * 0.5
    c0 = int(2.0 * SR); tb = t[:n - c0]
    sig[c0:] += _bell(tb, 523.25, 2.2, 0.42) + _bell(tb, 783.99, 2.2, 0.22)
    _write_wav(path, sig / (np.max(np.abs(sig)) or 1) * 0.85)


def make_outro_audio(path):
    n = int(CARD_SECONDS * SR); t = np.arange(n) / SR
    sig = np.zeros(n)
    env = np.clip(t / 1.0, 0, 1) * np.clip((CARD_SECONDS - t) / 1.2, 0, 1)
    sig += 0.12 * env * np.sin(2 * np.pi * 110.0 * t)
    sig += 0.08 * env * np.sin(2 * np.pi * 164.81 * t)
    c0 = int(0.6 * SR); tb = t[:n - c0]
    sig[c0:] += _bell(tb, 587.33, 2.6, 0.34) + _bell(tb, 880.0, 2.6, 0.18)
    _write_wav(path, sig / (np.max(np.abs(sig)) or 1) * 0.8)


# --------------------------------------------------------------------------- #
def encode(frames, wav, out_mp4, fps):
    subprocess.run([FFMPEG, "-y", "-framerate", str(fps),
                    "-i", os.path.join(frames, "f_%05d.png"), "-i", wav,
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                    "-crf", "16", "-preset", "medium", "-r", str(fps), "-vsync", "cfr",
                    "-c:a", "aac", "-ar", str(SR), "-ac", "2", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out_mp4], check=True)


def build(which, W, H, fps, outdir):
    import shutil
    svg = open(os.path.join(HERE, "vilvik_logo_animated.svg")).read()
    css = open(os.path.join(HERE, "draw-on.css")).read()
    html = card_html(svg, css, W, H)
    tag = "4k" if H >= 2160 else "%dp" % H
    work = os.path.join(outdir, ".work_%s" % tag)
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    frames = render_frames(html, work, W, H, fps)
    targets = ["intro", "outro"] if which == "both" else [which]
    for name in targets:
        wav = os.path.join(outdir, "vilvik_%s.wav" % name)
        (make_intro_audio if name == "intro" else make_outro_audio)(wav)
        out = os.path.join(outdir, "vilvik_%s_%s.mp4" % (name, tag))
        encode(frames, wav, out, fps)
        print("wrote", out)
    shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", choices=["intro", "outro", "both"], default="both")
    ap.add_argument("--res", choices=["1080", "4k"], default="1080")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--outdir", default=HERE)
    a = ap.parse_args()
    if a.width and a.height:
        W, H = a.width, a.height
    else:
        W, H = (3840, 2160) if a.res == "4k" else (1920, 1080)
    build(a.which, W, H, a.fps, a.outdir)


if __name__ == "__main__":
    main()
