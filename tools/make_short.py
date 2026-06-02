"""Make a vertical 9:16 Short / Reel from the 4K CoinTex promo material.

Builds a ~35s highlight: CoinTex title -> gameplay snippets from varied worlds
(Meadow / Ocean / Volcano / Space) -> Vilvik outro, then reframes 16:9 to
1080x1920 with a blurred fill behind the centered gameplay. Output suits YouTube
Shorts and Facebook/Instagram Reels (1080x1920, H.264/AAC, <60s).

Run: venv/bin/python tools/make_short.py
"""

import os
import shutil
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()

MEDIA = os.path.join(_ROOT, "cointex_media")
BUILD = os.path.join(MEDIA, ".cointex4k_build")
WORK = os.path.join(MEDIA, ".short_work")
OUTPUT = os.path.join(MEDIA, "cointex_ga_short_9x16.mp4")

TITLE = os.path.join(MEDIA, "cointex_title_4k.mp4")
OUTRO = os.path.join(BUILD, "zz_outro.mp4")

# (source clip, start sec, duration sec). Gameplay snippets are the opening
# seconds of each world segment (start with live gameplay).
SLICES = [
    (TITLE, 0.4, 3.2),                              # "CoinTex · Google Play"
    (os.path.join(BUILD, "seg0.mp4"), 0.0, 7.0),    # World 1 Meadow
    (os.path.join(BUILD, "seg2.mp4"), 0.0, 7.0),    # World 3 Ocean
    (os.path.join(BUILD, "seg4.mp4"), 0.0, 7.0),    # World 5 Volcano
    (os.path.join(BUILD, "seg5.mp4"), 0.0, 8.0),    # World 6 Space
    (OUTRO, 0.0, 4.5),                              # Vilvik outro
]

W, H, FPS, CRF = 1080, 1920, 60, 18


def trim(src, start, dur, out):
    # Trim and normalise to 1080p 16:9 / 60fps / stereo so all slices concat cleanly.
    subprocess.run([FF, "-y", "-ss", "%.3f" % start, "-i", src, "-t", "%.3f" % dur,
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                           "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=60",
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                    "-crf", str(CRF), "-preset", "fast",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    "-movflags", "+faststart", out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def concat(clips, out):
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    n = len(clips)
    streams = "".join("[%d:v][%d:a]" % (i, i) for i in range(n))
    fc = "%sconcat=n=%d:v=1:a=1[v][a]" % (streams, n)
    subprocess.run([FF, "-y", *inputs, "-filter_complex", fc, "-map", "[v]",
                    "-map", "[a]", "-c:v", "libx264", "-profile:v", "high",
                    "-pix_fmt", "yuv420p", "-crf", str(CRF), "-preset", "fast",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    out], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def reframe_vertical(src, out):
    # Blurred fill behind the centered 16:9 gameplay -> 1080x1920.
    vf = ("split=2[a][b];"
          "[a]scale=1080:1920:force_original_aspect_ratio=increase,"
          "crop=1080:1920,boxblur=26:1[bg];"
          "[b]scale=1080:-2[fg];"
          "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p")
    subprocess.run([FF, "-y", "-i", src, "-vf", vf,
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                    "-crf", str(CRF), "-preset", "medium", "-r", str(FPS),
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    "-movflags", "+faststart", out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    clips = []
    for i, (src, start, dur) in enumerate(SLICES):
        if not os.path.exists(src):
            sys.exit("missing source: " + src)
        c = os.path.join(WORK, "s%02d.mp4" % i)
        trim(src, start, dur, c)
        clips.append(c)
        print("trimmed %s (%.1fs)" % (os.path.basename(src), dur), flush=True)
    montage = os.path.join(WORK, "montage_16x9.mp4")
    concat(clips, montage)
    print("concatenated montage", flush=True)
    reframe_vertical(montage, OUTPUT)
    shutil.rmtree(WORK, ignore_errors=True)
    print("DONE ->", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
