"""Build the brand-new 4K/60 CoinTex gameplay clips (cards + 6 world segments).

Per world: capture each level ATTEMPT as its own clip (tools/capture_cointex.py
under Xvfb), then assemble keeping only the longest FAILED attempt + the SUCCESS
per level (if a level is never cleared, only its longest failure). Mix each
segment's soundtrack (world music + synced SFX) and mux.

Resumable: a world whose seg{i}.mp4 already exists is skipped, so a pause /
reboot only costs the unfinished worlds. Produces the intermediates that
tools/finalize_cointex_4k.py concatenates (with the CoinTex title) into the
final video. Run: venv/bin/python tools/make_cointex_4k.py
"""

import json
import os
import shutil
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import make_vilvik_promo as M          # card renderer + ffmpeg path
import mix_cointex_audio as mixer

M.W, M.H = 3840, 2160
M.FPS = 60
M.CARD_FRAMES = int(round(M.CARD_SECONDS * 60))

FF = M.FFMPEG
MEDIA = M.MEDIA
MUSIC_DIR = os.path.join(_ROOT, "music")
BUILD = os.path.join(MEDIA, ".cointex4k_build")

SIZE = "3840x2160"
FPS = 60
CRF = 16
SECONDS = 18.0
MAX_SECONDS = 60.0
LEVELS = [1, 11, 21, 31, 41, 51]   # start level of each world; --chain plays on
XVFB = ["xvfb-run", "-a", "-s", "-screen 0 3840x2160x24"]


def capture_world(level, outdir):
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    cmd = XVFB + [
        os.path.join(_ROOT, "venv/bin/python"),
        os.path.join(_ROOT, "tools/capture_cointex.py"),
        "--level", str(level), "--size", SIZE, "--fps", str(FPS),
        "--seconds", str(SECONDS), "--max-seconds", str(MAX_SECONDS),
        "--max-retries", "3", "--crf", str(CRF),
        "--chain", "--outdir", outdir,
    ]
    subprocess.run(cmd, cwd=_ROOT, check=True, timeout=2400)


def select_attempts(manifest):
    """Per level keep the longest FAILED attempt (if any) then the SUCCESS."""
    order, bylevel = [], {}
    for a in manifest["attempts"]:
        bylevel.setdefault(a["level"], []).append(a)
        if a["level"] not in order:
            order.append(a["level"])
    sel = []
    for lvl in order:
        grp = bylevel[lvl]
        loses = [a for a in grp if a["outcome"] == "lose"]
        win = next((a for a in grp if a["outcome"] == "win"), None)
        if loses:
            sel.append(max(loses, key=lambda a: a["frames"]))
        if win:
            sel.append(win)
    return sel


def concat_copy(files, out):
    listfile = out + ".txt"
    with open(listfile, "w") as f:
        for p in files:
            f.write("file '%s'\n" % os.path.abspath(p))
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                    "-c", "copy", "-movflags", "+faststart", out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    os.remove(listfile)


def mux(seg_video, seg_wav, out_mp4):
    subprocess.run(
        [FF, "-y", "-i", seg_video, "-i", seg_wav,
         "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2",
         "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def assemble_world(outdir, seg_mp4):
    manifest = json.load(open(os.path.join(outdir, "manifest.json")))
    fps = manifest["fps"]
    sel = select_attempts(manifest)
    if not sel:
        raise RuntimeError("no attempts captured in " + outdir)
    files = [os.path.join(outdir, a["file"]) for a in sel]
    seg_video = os.path.join(outdir, "selected_video.mp4")
    concat_copy(files, seg_video)

    combined, offset = [], 0
    for a in sel:
        for e in a["events"]:
            combined.append({"t": e["t"] + offset / fps, "name": e["name"]})
        offset += a["frames"]
    seconds = offset / float(fps)
    seg_wav = os.path.join(outdir, "selected.wav")
    mixer.build_mix_events(combined, manifest["world"], seconds, seg_wav, MUSIC_DIR)
    mux(seg_video, seg_wav, seg_mp4)
    return seconds, len(sel)


def encode_card_4k(frames_dir, wav, out_mp4):
    subprocess.run(
        [FF, "-y", "-framerate", str(FPS),
         "-i", os.path.join(frames_dir, "f_%05d.png"), "-i", wav,
         "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-crf", str(CRF), "-preset", "medium", "-r", str(FPS), "-vsync", "cfr",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", out_mp4],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def build_cards():
    intro_mp4 = os.path.join(BUILD, "00_intro.mp4")
    outro_mp4 = os.path.join(BUILD, "zz_outro.mp4")
    if os.path.exists(intro_mp4) and os.path.exists(outro_mp4):
        print("== Vilvik cards present, skipping ==", flush=True)
        return
    print("== rendering 4K Vilvik cards ==", flush=True)
    html = M.card_html(M.extract_logo_svg(), M.extract_drawon_css())
    intro_frames = M.render_card("intro", html)
    outro_frames = M.render_card("outro", html)
    intro_wav = os.path.join(BUILD, "intro.wav")
    outro_wav = os.path.join(BUILD, "outro.wav")
    M.make_intro_audio(intro_wav)
    M.make_outro_audio(outro_wav)
    encode_card_4k(intro_frames, intro_wav, intro_mp4)
    encode_card_4k(outro_frames, outro_wav, outro_mp4)


def main():
    os.makedirs(BUILD, exist_ok=True)
    build_cards()
    for i, level in enumerate(LEVELS):
        seg_mp4 = os.path.join(BUILD, "seg%d.mp4" % i)
        if os.path.exists(seg_mp4):
            print("== world %d present, skipping ==" % (i + 1), flush=True)
            continue
        print("== capturing world %d (start level %d) ==" % (i + 1, level), flush=True)
        outdir = os.path.join(BUILD, "world%d" % i)
        capture_world(level, outdir)
        secs, nclips = assemble_world(outdir, seg_mp4)
        print("   world %d: %.1fs from %d clips" % (i + 1, secs, nclips), flush=True)
    print("\nDONE building segments. Run finalize_cointex_4k.py to assemble.",
          flush=True)


if __name__ == "__main__":
    main()
