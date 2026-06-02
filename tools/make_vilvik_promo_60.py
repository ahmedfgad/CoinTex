#!/usr/bin/env python3
"""Build the 60fps Vilvik promo.

Reuses make_vilvik_promo's card rendering (now at true 60fps), and bookends a
cut + 60fps-converted copy of the source. The two edits already applied to the
30fps deliverable collapse into a single contiguous source cut:
  promo cut1 [2:13,2:31] -> source [128.5, 146.5]
  promo cut2 residual     -> source [146.5, 147.167]
so the net removed span is source [128.5, 147.167].

Gameplay is natively 30fps and is frame-doubled into the 60fps timeline (no
interpolation). The logo animations are rendered natively at 60fps.

Output: cointex_media/cointex_ga_intro_sfx_vilvik_1080p_60fps.mp4
"""
import os
import sys
import shutil
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import make_vilvik_promo as M  # noqa: E402

# Switch the shared pipeline to 60fps.
M.FPS = 60
M.CARD_FRAMES = int(round(M.CARD_SECONDS * 60))   # 270

FF = M.FFMPEG
BUILD = M.BUILD
SOURCE = M.SOURCE
OUTPUT = os.path.join(M.MEDIA, "cointex_ga_intro_sfx_vilvik_1080p_60fps.mp4")

CUT_A = 128.5      # net contiguous cut start in source seconds
CUT_B = 147.167    # net contiguous cut end


def cut_source_60(out_mp4):
    cmd = [
        FF, "-y", "-i", SOURCE, "-filter_complex",
        (f"[0:v]trim=0:{CUT_A},setpts=PTS-STARTPTS[v0];"
         f"[0:a]atrim=0:{CUT_A},asetpts=PTS-STARTPTS[a0];"
         f"[0:v]trim={CUT_B},setpts=PTS-STARTPTS[v1];"
         f"[0:a]atrim={CUT_B},asetpts=PTS-STARTPTS[a1];"
         f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"),
        "-map", "[v]", "-map", "[a]", "-r", "60",
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-ar", str(M.SR), "-ac", "1", "-b:a", "137k",
        "-movflags", "+faststart", out_mp4,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.STDOUT)


def concat(intro_mp4, src60, outro_mp4, out):
    listfile = os.path.join(BUILD, "concat60.txt")
    with open(listfile, "w") as f:
        for p in (intro_mp4, src60, outro_mp4):
            f.write(f"file '{p}'\n")
    r = subprocess.run(
        [FF, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
         "-c", "copy", "-movflags", "+faststart", out],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print(r.stdout)
        raise RuntimeError("concat (stream-copy) failed")


def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    print("1/5 extracting logo + draw-on css")
    svg = M.extract_logo_svg()
    css = M.extract_drawon_css()
    html = M.card_html(svg, css)

    print("2/5 rendering intro/outro frames @60fps")
    intro_frames = M.render_card("intro", html)
    outro_frames = M.render_card("outro", html)

    print("3/5 synthesizing audio")
    intro_wav = os.path.join(BUILD, "intro.wav")
    outro_wav = os.path.join(BUILD, "outro.wav")
    M.make_intro_audio(intro_wav)
    M.make_outro_audio(outro_wav)

    print("4/5 encoding cards + cut/60fps source")
    intro_mp4 = os.path.join(BUILD, "intro.mp4")
    outro_mp4 = os.path.join(BUILD, "outro.mp4")
    M.encode_card(intro_frames, intro_wav, intro_mp4)
    M.encode_card(outro_frames, outro_wav, outro_mp4)
    src60 = os.path.join(BUILD, "source60.mp4")
    cut_source_60(src60)

    print("5/5 concatenating")
    concat(intro_mp4, src60, outro_mp4, OUTPUT)
    print(f"\nDONE -> {OUTPUT}")


if __name__ == "__main__":
    main()
