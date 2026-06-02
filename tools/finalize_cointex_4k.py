"""Assemble the final 4K/60 CoinTex promo and emit YouTube chapters.

Order: Vilvik intro -> CoinTex title (Available on Google Play) -> six world
gameplay segments -> Vilvik outro. Reuses the clips left in the gameplay build
dir plus the standalone CoinTex title card. Prints/writes chapter timestamps
computed from each clip's real duration.
"""

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()

MEDIA = os.path.join(_ROOT, "cointex_media")
BUILD = os.path.join(MEDIA, ".cointex4k_build")
TITLE = os.path.join(MEDIA, "cointex_title_4k.mp4")
OUTPUT = os.path.join(MEDIA, "cointex_ga_4k_60fps.mp4")
CHAPTERS = os.path.join(MEDIA, "cointex_ga_4k_chapters.txt")

WORLDS = ["Meadow", "Desert", "Ocean", "Cavern", "Volcano", "Space"]
CRF = 16


def dur(path):
    out = subprocess.run([FF, "-hide_banner", "-i", path],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True).stdout
    for tok in out.split():
        if tok.startswith("00:"):
            h, m, s = tok.strip(",").split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("no duration for " + path)


def concat(clips, out):
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    n = len(clips)
    streams = "".join("[%d:v][%d:a]" % (i, i) for i in range(n))
    fc = "%sconcat=n=%d:v=1:a=1[v][a]" % (streams, n)
    subprocess.run(
        [FF, "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-crf", str(CRF), "-preset", "medium",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
         "-movflags", "+faststart", out],
        check=True)


def ts(seconds):
    seconds = int(round(seconds))
    return "%d:%02d" % (seconds // 60, seconds % 60)


def main():
    intro = os.path.join(BUILD, "00_intro.mp4")
    outro = os.path.join(BUILD, "zz_outro.mp4")
    segs = [os.path.join(BUILD, "seg%d.mp4" % i) for i in range(6)]
    clips = [intro, TITLE] + segs + [outro]
    for c in clips:
        if not os.path.exists(c):
            sys.exit("missing clip: " + c)

    print("concatenating final 4K video (%d clips)..." % len(clips))
    concat(clips, OUTPUT)

    # Chapters from real durations.
    lines = ["0:00 Intro"]
    t = dur(intro) + dur(TITLE)          # first gameplay starts after both cards
    for i, seg in enumerate(segs):
        lines.append("%s World %d - %s" % (ts(t), i + 1, WORLDS[i]))
        t += dur(seg)
    lines.append("%s Outro" % ts(t))
    text = "\n".join(lines) + "\n"
    with open(CHAPTERS, "w") as f:
        f.write(text)
    print("\n=== YouTube chapters ===")
    print(text)
    print("wrote", CHAPTERS)
    print("DONE ->", OUTPUT)


if __name__ == "__main__":
    main()
