"""Render the CoinTex title intro card at 4K/60.

Recreates the original game intro — the CoinTex app icon animating in, the
"CoinTex" title, and "Available on Google Play" — on the same dark navy
backdrop as the Vilvik cards, but with the personal GitHub line replaced by
vilvik.com. Output: cointex_media/cointex_title_4k.mp4 (H.264/AAC, ~3.8s).

Reuses make_vilvik_promo's deterministic chrome-headless frame renderer.
"""

import base64
import os
import subprocess
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import make_vilvik_promo as M

W, H = 3840, 2160
FPS = 60
SECONDS = 3.8
CRF = 16

M.W, M.H = W, H
M.FPS = FPS
M.CARD_FRAMES = int(round(SECONDS * FPS))
M.BUILD = os.path.join(M.MEDIA, ".cointex_title_build")

ICON = os.path.join(_ROOT, "cointex_logo.png")
OUTPUT = os.path.join(M.MEDIA, "cointex_title_4k.mp4")


def _icon_data_uri():
    with open(ICON, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return "data:image/png;base64," + b64


def card_html():
    s = H / 1080.0
    icon = _icon_data_uri()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#070c18;
  font-family:'DejaVu Sans','Liberation Sans',sans-serif;}}
.bg{{position:fixed;inset:0;background:
  radial-gradient(ellipse 80% 75% at 50% 42%, #1b2c4d 0%, #101a33 48%, #070c18 100%);}}
/* faint bokeh discs, like the original intro */
.bokeh{{position:fixed;inset:0;overflow:hidden;opacity:.5}}
.bokeh i{{position:absolute;border-radius:50%;
  background:radial-gradient(circle, rgba(80,120,200,.18), rgba(80,120,200,0) 70%);}}
.stage{{position:fixed;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:{34*s:.1f}px;}}
.icon{{width:{300*s:.1f}px;height:{300*s:.1f}px;border-radius:{66*s:.1f}px;
  box-shadow:0 {18*s:.1f}px {44*s:.1f}px rgba(0,0,0,.45);
  animation:icon-in .95s cubic-bezier(.34,1.4,.5,1) both,
            bob 3.6s ease-in-out infinite 1.2s;}}
@keyframes icon-in{{0%{{opacity:0;transform:scale(.35) rotate(-28deg)}}
  60%{{opacity:1;transform:scale(1.08) rotate(7deg)}}
  100%{{opacity:1;transform:scale(1) rotate(0)}}}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY({-10*s:.1f}px)}}}}
.title{{font-size:{120*s:.1f}px;font-weight:bold;color:#f4c20a;letter-spacing:.01em;
  text-shadow:0 {3*s:.1f}px {16*s:.1f}px rgba(0,0,0,.5);
  opacity:0;animation:rise .7s ease-out both .85s;}}
.gp{{font-size:{46*s:.1f}px;font-weight:bold;color:#eef3ff;letter-spacing:.02em;
  opacity:0;animation:rise .7s ease-out both 1.2s;}}
.site{{font-size:{34*s:.1f}px;font-weight:300;color:#7f9bd6;letter-spacing:.22em;
  text-indent:.22em;opacity:0;animation:rise .7s ease-out both 1.55s;}}
@keyframes rise{{0%{{opacity:0;transform:translateY({16*s:.1f}px)}}
  100%{{opacity:1;transform:translateY(0)}}}}
.blackout{{position:fixed;inset:0;background:#000;pointer-events:none;
  animation:blackout {SECONDS}s linear both;}}
@keyframes blackout{{0%{{opacity:1}}11%{{opacity:0}}88%{{opacity:0}}100%{{opacity:1}}}}
</style></head>
<body>
  <div class="bg"></div>
  <div class="bokeh">
    <i style="width:{420*s:.0f}px;height:{420*s:.0f}px;left:8%;top:18%"></i>
    <i style="width:{300*s:.0f}px;height:{300*s:.0f}px;left:74%;top:12%"></i>
    <i style="width:{520*s:.0f}px;height:{520*s:.0f}px;left:60%;top:60%"></i>
    <i style="width:{260*s:.0f}px;height:{260*s:.0f}px;left:18%;top:66%"></i>
  </div>
  <div class="stage">
    <img class="icon" src="{icon}" alt="CoinTex">
    <div class="title">CoinTex</div>
    <div class="gp">Available on Google Play</div>
    <div class="site">vilvik.com</div>
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


def make_audio(path):
    n = int(SECONDS * M.SR)
    t = np.arange(n) / M.SR
    sig = np.zeros(n, np.float32)
    # bright coin-style chime as the icon lands (~0.9s)
    c0 = int(0.9 * M.SR)
    tb = t[:n - c0]
    sig[c0:] += M._bell(tb, 783.99, 1.8, 0.34)   # G5
    sig[c0:] += M._bell(tb, 1174.66, 1.8, 0.20)  # D6
    # soft sparkle a touch later
    c1 = int(1.25 * M.SR)
    tb2 = t[:n - c1]
    sig[c1:] += M._bell(tb2, 1567.98, 1.4, 0.14)  # G6
    peak = float(np.max(np.abs(sig))) or 1.0
    M.write_wav(path, sig / peak * 0.8)


def encode(frames_dir, wav, out_mp4):
    subprocess.run(
        [M.FFMPEG, "-y", "-framerate", str(FPS),
         "-i", os.path.join(frames_dir, "f_%05d.png"), "-i", wav,
         "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-crf", str(CRF), "-preset", "medium", "-r", str(FPS), "-vsync", "cfr",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", out_mp4],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    import shutil
    if os.path.exists(M.BUILD):
        shutil.rmtree(M.BUILD)
    os.makedirs(M.BUILD)
    frames = M.render_card("cointex_title", card_html())
    wav = os.path.join(M.BUILD, "title.wav")
    make_audio(wav)
    encode(frames, wav, OUTPUT)
    print("DONE ->", OUTPUT)


if __name__ == "__main__":
    main()
