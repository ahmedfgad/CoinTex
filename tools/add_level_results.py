"""Add per-level pass/fail result screens to the 4K promo WITHOUT re-capturing.

Reuses the per-attempt gameplay clips already saved under
cointex_media/.cointex4k_build/world*/ and, after each SELECTED clip, splices a
short result screen matching its outcome ("Level Clear!" with stars, or
"You were caught!") drawn over a dimmed freeze of that clip's last frame — the
way the game shows it. Rebuilds each world's soundtrack (music + gameplay SFX +
the victory/death sting) and overwrites seg{i}.mp4. Then run
finalize_cointex_4k.py to produce the final video.

Run: venv/bin/python tools/add_level_results.py
"""

import base64
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import make_vilvik_promo as M
import make_cointex_4k as O
import mix_cointex_audio as mixer

FF = O.FF
CHS = M.CHS
BUILD = O.BUILD
MUSIC_DIR = O.MUSIC_DIR
W, H, FPS, CRF = 3840, 2160, 60, 16
RESULT_SECONDS = 1.5
RESULT_FRAMES = int(round(RESULT_SECONDS * FPS))


def _last_frame_png(clip, out_png):
    subprocess.run([FF, "-y", "-sseof", "-0.15", "-i", clip, "-update", "1",
                    "-frames:v", "1", out_png],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def _data_uri(png):
    with open(png, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def _result_html(bg_uri, won):
    s = H / 1080.0
    title = "Level Clear!" if won else "You were caught!"
    stars = ('<div class="stars">' + "★★★" + "</div>") if won else ""
    if won:
        b1, b1c = "Menu", "#6f7682"
        b2, b2c = "Next", "#2fb86a"
    else:
        b1, b1c = "Menu", "#6f7682"
        b2, b2c = "Retry", "#e8912a"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;
  font-family:'DejaVu Sans','Liberation Sans',sans-serif}}
.bg{{position:fixed;inset:0;background:#0a0f1a center/cover no-repeat;
  background-image:url('{bg_uri}');filter:brightness(.42)}}
.panel{{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);
  width:{1980*s:.0f}px;background:#1b2a48;border:{2*s:.0f}px solid #2c3e63;
  border-radius:{34*s:.0f}px;padding:{70*s:.0f}px {90*s:.0f}px;
  box-shadow:0 {24*s:.0f}px {70*s:.0f}px rgba(0,0,0,.55);
  display:flex;flex-direction:column;align-items:center;gap:{48*s:.0f}px;}}
.title{{font-size:{96*s:.0f}px;font-weight:bold;color:#f4c20a;
  text-shadow:0 {2*s:.0f}px {10*s:.0f}px rgba(0,0,0,.5)}}
.stars{{font-size:{150*s:.0f}px;color:#f4c20a;letter-spacing:{30*s:.0f}px;
  line-height:1;text-shadow:0 {3*s:.0f}px {12*s:.0f}px rgba(0,0,0,.45)}}
.btns{{display:flex;gap:{40*s:.0f}px;width:100%;margin-top:{8*s:.0f}px}}
.btn{{flex:1;text-align:center;color:#fff;font-size:{46*s:.0f}px;font-weight:bold;
  padding:{40*s:.0f}px 0;border-radius:{20*s:.0f}px}}
</style></head><body>
  <div class="bg"></div>
  <div class="panel">
    <div class="title">{title}</div>
    {stars}
    <div class="btns">
      <div class="btn" style="background:{b1c}">{b1}</div>
      <div class="btn" style="background:{b2c}">{b2}</div>
    </div>
  </div>
</body></html>"""


def _render_result_clip(clip_video, won, work, idx, out_mp4):
    bg_png = os.path.join(work, "bg_%d.png" % idx)
    _last_frame_png(clip_video, bg_png)
    html = os.path.join(work, "res_%d.html" % idx)
    with open(html, "w") as f:
        f.write(_result_html(_data_uri(bg_png), won))
    png = os.path.join(work, "res_%d.png" % idx)
    prof = os.path.join(work, "prof_%d" % idx)
    subprocess.run([CHS, "--no-sandbox", "--user-data-dir=" + prof,
                    "--no-first-run", "--no-default-browser-check",
                    "--hide-scrollbars", "--disable-gpu",
                    "--window-size=%d,%d" % (W, H), "--force-device-scale-factor=1",
                    "--virtual-time-budget=800",
                    "--run-all-compositor-stages-before-draw",
                    "--screenshot=" + png, "file://" + html],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    # Hold the still as a clip, matching the gameplay clips' encoder flags so the
    # per-world concat can stream-copy. Brief fade-in from black.
    subprocess.run([FF, "-y", "-loop", "1", "-framerate", str(FPS), "-i", png,
                    "-t", "%.3f" % RESULT_SECONDS,
                    "-vf", "fade=t=in:st=0:d=0.12,format=yuv420p",
                    "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", str(CRF), "-preset", "fast", "-an",
                    "-movflags", "+faststart", out_mp4],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def process_world(i):
    outdir = os.path.join(BUILD, "world%d" % i)
    manifest = json.load(open(os.path.join(outdir, "manifest.json")))
    fps = manifest["fps"]
    sel = O.select_attempts(manifest)

    video_clips, combined, offset = [], [], 0
    for k, a in enumerate(sel):
        won = a["outcome"] == "win"
        gp = os.path.join(outdir, a["file"])
        video_clips.append(gp)
        for e in a["events"]:
            combined.append({"t": e["t"] + offset / fps, "name": e["name"]})
        offset += a["frames"]
        # result screen for this clip
        res = os.path.join(outdir, "result_%d.mp4" % k)
        _render_result_clip(gp, won, outdir, k, res)
        video_clips.append(res)
        combined.append({"t": offset / fps, "name": "victory" if won else "death"})
        offset += RESULT_FRAMES

    seg_video = os.path.join(outdir, "withresults_video.mp4")
    O.concat_copy(video_clips, seg_video)
    seconds = offset / float(fps)
    seg_wav = os.path.join(outdir, "withresults.wav")
    mixer.build_mix_events(combined, manifest["world"], seconds, seg_wav, MUSIC_DIR)
    seg_mp4 = os.path.join(BUILD, "seg%d.mp4" % i)
    O.mux(seg_video, seg_wav, seg_mp4)
    return seconds, len(sel)


def main():
    for i in range(6):
        secs, n = process_world(i)
        print("world %d: %.1fs (%d levels + results)" % (i + 1, secs, n), flush=True)
    print("DONE adding results. Run finalize_cointex_4k.py.", flush=True)


if __name__ == "__main__":
    main()
