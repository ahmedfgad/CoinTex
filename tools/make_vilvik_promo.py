#!/usr/bin/env python3
"""Build a Vilvik-branded promo version of a CoinTex video.

Bookends an existing 1080p/30fps video with an animated Vilvik intro and outro
card. The logo uses the real "draw-on" choreography from the vilvik.com site
(the actual SVG mark + draw-on.css are pulled from the vilvik repo), rendered
deterministically by freezing the CSS animations at each frame's timestamp via
the Web Animations API and screenshotting with chrome-headless-shell. Cards are
encoded to match the source codec exactly so the source is concatenated by
stream-copy (no re-encode, no quality loss).

Outputs: cointex_media/cointex_ga_intro_sfx_vilvik_1080p.mp4
"""

import os
import re
import sys
import wave
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
COINTEX = os.path.dirname(HERE)
MEDIA = os.path.join(COINTEX, "cointex_media")
SOURCE = os.path.join(MEDIA, "cointex_ga_intro_sfx_1080p.mp4")
OUTPUT = os.path.join(MEDIA, "cointex_ga_intro_sfx_vilvik_1080p.mp4")
BUILD = os.path.join(MEDIA, ".vilvik_build")

VILVIK = "/home/ahmed-gad/projects/vilvik"
LOGO_HTML = os.path.join(
    VILVIK, "pygadproject/homeapp/templates/home/_animated_logo_mark.html")
DRAWON_CSS = os.path.join(
    VILVIK, "pygadproject/assets/css/logo-animations/draw-on.css")

FFMPEG = os.path.join(
    COINTEX,
    "venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/"
    "ffmpeg-linux-x86_64-v7.0.2")
CHS = ("/home/ahmed-gad/.cache/ms-playwright/chromium_headless_shell-1223/"
       "chrome-headless-shell-linux64/chrome-headless-shell")

# ---------------------------------------------------------------------------
# Video constants
# ---------------------------------------------------------------------------
W, H = 1920, 1080
FPS = 30
CARD_SECONDS = 4.5
CARD_FRAMES = int(round(CARD_SECONDS * FPS))   # 135
SR = 44100                                     # audio sample rate (mono)
WORKERS = 6


# ---------------------------------------------------------------------------
# 1. Extract the real Vilvik logo SVG + draw-on CSS from the vilvik repo
# ---------------------------------------------------------------------------
def extract_logo_svg():
    """Pull the 6-part SVG (incl. the draw-on stroke clones) from the Django
    partial, stripping all template tags."""
    txt = open(LOGO_HTML, encoding="utf-8").read()
    svg = txt[txt.index("<svg"):txt.index("</svg>") + len("</svg>")]
    # Drop {% comment %}...{% endcomment %} blocks and any {% ... %} tags,
    # keeping the draw-on stroke group that lived inside {% if %}/{% endif %}.
    svg = re.sub(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", "",
                 svg, flags=re.S)
    svg = re.sub(r"\{%.*?%\}", "", svg, flags=re.S)
    svg = re.sub(r"\{\{.*?\}\}", "", svg, flags=re.S)
    return svg.strip()


def extract_drawon_css():
    """Pull draw-on.css, dropping the prefers-reduced-motion block so the
    animation always plays in headless capture."""
    css = open(DRAWON_CSS, encoding="utf-8").read()
    css = re.sub(r"@media\s*\(prefers-reduced-motion[^{]*\)\s*\{.*?\}\s*\}",
                 "", css, flags=re.S)
    return css.strip()


# ---------------------------------------------------------------------------
# 2. Card HTML
# ---------------------------------------------------------------------------
def card_html(svg, drawon_css):
    s = H / 1080.0   # scale the fixed-px layout to the render resolution (4K-ready)
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

/* ---- draw-on choreography (verbatim from vilvik.com draw-on.css) ---- */
{drawon_css}
</style></head>
<body>
  <div class="bg"></div>
  <div class="stage">
    <div class="content">
      <div class="logo-wrap">
        <div class="vlogo-anim vlogo-anim--once vlogo-anim--color vlogo-anim--draw-on">
          {svg}
        </div>
      </div>
      <div class="wordmark">vilvik.com</div>
    </div>
  </div>
  <div class="blackout"></div>
  <script>
    const T = parseFloat(new URLSearchParams(location.search).get('t') || '0');
    function freeze(){{document.getAnimations().forEach(a=>{{a.pause();a.currentTime=T;}});}}
    freeze();
    requestAnimationFrame(()=>{{freeze();requestAnimationFrame(freeze);}});
  </script>
</body></html>
"""


# ---------------------------------------------------------------------------
# 3. Frame rendering (parallel headless-shell, deterministic via ?t=)
# ---------------------------------------------------------------------------
_profile = None


def _init_worker(profiles_base):
    global _profile
    _profile = os.path.join(profiles_base, f"p{os.getpid()}")
    os.makedirs(_profile, exist_ok=True)


def _render_frame(args):
    html_path, out_png, t_ms = args
    cmd = [
        CHS, "--no-sandbox", f"--user-data-dir={_profile}",
        "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
        "--disable-gpu", f"--window-size={W},{H}",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=700", "--run-all-compositor-stages-before-draw",
        f"--screenshot={out_png}", f"file://{html_path}?t={t_ms:.3f}",
    ]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
    if r.returncode != 0 or not os.path.exists(out_png):
        raise RuntimeError(f"render failed t={t_ms} rc={r.returncode}")
    return out_png


def render_card(name, html_text):
    html_path = os.path.join(BUILD, f"{name}.html")
    open(html_path, "w", encoding="utf-8").write(html_text)
    frames_dir = os.path.join(BUILD, f"{name}_frames")
    os.makedirs(frames_dir, exist_ok=True)
    profiles_base = os.path.join(BUILD, f"{name}_profiles")
    os.makedirs(profiles_base, exist_ok=True)

    tasks = []
    for i in range(CARD_FRAMES):
        t_ms = (i / FPS) * 1000.0
        tasks.append((html_path,
                      os.path.join(frames_dir, f"f_{i:05d}.png"), t_ms))

    print(f"  rendering {CARD_FRAMES} frames for {name} "
          f"({WORKERS} workers)...", flush=True)
    with ProcessPoolExecutor(max_workers=WORKERS,
                             initializer=_init_worker,
                             initargs=(profiles_base,)) as ex:
        done = 0
        for _ in ex.map(_render_frame, tasks):
            done += 1
            if done % 30 == 0 or done == CARD_FRAMES:
                print(f"    {name}: {done}/{CARD_FRAMES}", flush=True)
    return frames_dir


# ---------------------------------------------------------------------------
# 4. Audio synthesis (NumPy) -> wav
# ---------------------------------------------------------------------------
def _bell(t, f0, dur, amp):
    """Inharmonic bell: a few partials with exponential decay."""
    env = np.exp(-t / (dur * 0.32)) * (t >= 0)
    parts = [(1.0, 1.00), (2.76, 0.55), (5.40, 0.32), (8.93, 0.18)]
    sig = np.zeros_like(t)
    for ratio, a in parts:
        sig += a * np.sin(2 * np.pi * f0 * ratio * t)
    return amp * env * sig


def _whoosh(t, dur):
    """Rising filtered-noise sweep that swells then settles."""
    n = len(t)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    # one-pole low-pass whose cutoff opens up over time -> brightening sweep
    out = np.zeros(n)
    prev = 0.0
    for i in range(n):
        frac = min(i / (dur * SR), 1.0)
        a = 0.0025 + 0.05 * frac            # rising cutoff coefficient
        prev = prev + a * (noise[i] - prev)
        out[i] = prev
    swell = np.clip(t / 1.6, 0, 1) ** 1.4
    fall = np.exp(-np.clip(t - 1.7, 0, None) / 0.9)
    return out * swell * fall * 9.0


def write_wav(path, samples):
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def make_intro_audio(path):
    n = int(CARD_SECONDS * SR)
    t = np.arange(n) / SR
    sig = _whoosh(t, CARD_SECONDS) * 0.5
    # chime lands as the mark completes (~2.0s)
    c0 = int(2.0 * SR)
    tb = t[:n - c0]
    sig[c0:] += _bell(tb, 523.25, 2.2, 0.42)     # C5
    sig[c0:] += _bell(tb, 783.99, 2.2, 0.22)     # G5
    peak = np.max(np.abs(sig)) or 1.0
    write_wav(path, sig / peak * 0.85)


def make_outro_audio(path):
    n = int(CARD_SECONDS * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    # low warm pad through the whole card
    pad_env = np.clip(t / 1.0, 0, 1) * np.clip((CARD_SECONDS - t) / 1.2, 0, 1)
    sig += 0.12 * pad_env * np.sin(2 * np.pi * 110.0 * t)
    sig += 0.08 * pad_env * np.sin(2 * np.pi * 164.81 * t)
    # soft chime as the mark assembles (~0.6s)
    c0 = int(0.6 * SR)
    tb = t[:n - c0]
    sig[c0:] += _bell(tb, 587.33, 2.6, 0.34)     # D5
    sig[c0:] += _bell(tb, 880.00, 2.6, 0.18)     # A5
    peak = np.max(np.abs(sig)) or 1.0
    write_wav(path, sig / peak * 0.8)


# ---------------------------------------------------------------------------
# 5. Encode cards + concat
# ---------------------------------------------------------------------------
def encode_card(frames_dir, wav, out_mp4):
    cmd = [
        FFMPEG, "-y",
        "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f_%05d.png"),
        "-i", wav,
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-vsync", "cfr",
        "-c:a", "aac", "-ar", str(SR), "-ac", "1", "-b:a", "137k",
        "-shortest", "-movflags", "+faststart", out_mp4,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.STDOUT)


def concat(intro_mp4, outro_mp4, out):
    listfile = os.path.join(BUILD, "concat.txt")
    with open(listfile, "w") as f:
        for p in (intro_mp4, SOURCE, outro_mp4):
            f.write(f"file '{p}'\n")
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
           "-c", "copy", "-movflags", "+faststart", out]
    r = subprocess.run(cmd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print(r.stdout)
        raise RuntimeError("concat (stream-copy) failed")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    for p in (SOURCE, FFMPEG, CHS, LOGO_HTML, DRAWON_CSS):
        if not os.path.exists(p):
            sys.exit(f"missing required path: {p}")

    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    print("1/5 extracting logo + draw-on css from vilvik repo")
    svg = extract_logo_svg()
    css = extract_drawon_css()
    html = card_html(svg, css)

    print("2/5 rendering intro/outro frames")
    intro_frames = render_card("intro", html)
    outro_frames = render_card("outro", html)

    print("3/5 synthesizing audio")
    intro_wav = os.path.join(BUILD, "intro.wav")
    outro_wav = os.path.join(BUILD, "outro.wav")
    make_intro_audio(intro_wav)
    make_outro_audio(outro_wav)

    print("4/5 encoding cards")
    intro_mp4 = os.path.join(BUILD, "intro.mp4")
    outro_mp4 = os.path.join(BUILD, "outro.mp4")
    encode_card(intro_frames, intro_wav, intro_mp4)
    encode_card(outro_frames, outro_wav, outro_mp4)

    print("5/5 concatenating (source stream-copied)")
    concat(intro_mp4, outro_mp4, OUTPUT)

    print(f"\nDONE -> {OUTPUT}")


if __name__ == "__main__":
    main()
