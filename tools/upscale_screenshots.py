"""Upscale the 8 Play-Store screenshots from 1280x720 to 1920x1080.

Play Console (tablet listing) requires 16:9 or 9:16, with each side between
1080 and 7680 px. The originals are already 16:9 but 720 px on the short
side, which is below the minimum.

LANCZOS resampling is used; CoinTex's art is flat-colored and vector-like,
so 1.5x upscaling preserves quality well. Originals stay untouched; the
upscaled files land in cointex_media/tablet_screenshots/.
"""

from __future__ import annotations

import os
from PIL import Image

SRC_DIR = "cointex_media"
DST_DIR = os.path.join("cointex_media", "tablet_screenshots")
TARGET = (1920, 1080)  # 16:9, both sides within [1080, 7680]

NAMES = [
    "01_menu.png",
    "02_worldmap.png",
    "03_levelselect.png",
    "04_gameplay.png",
    "05_combat_chasers.png",
    "06_win_stars.png",
    "07_auto_player.png",
    "08_guide.png",
]


def main():
    os.makedirs(DST_DIR, exist_ok=True)
    for name in NAMES:
        src = os.path.join(SRC_DIR, name)
        dst = os.path.join(DST_DIR, name)
        im = Image.open(src)
        w, h = im.size
        # Sanity: the source must already be 16:9 so no cropping/letterboxing.
        if abs(w / h - 16 / 9) > 0.01:
            raise SystemExit("{} is not 16:9 ({}x{})".format(src, w, h))
        out = im.convert("RGB").resize(TARGET, Image.LANCZOS)
        out.save(dst, "PNG", optimize=True)
        kb = os.path.getsize(dst) / 1024.0
        print("{:<26} {}x{} -> {}x{}  ({:.1f} KB)".format(
            name, w, h, TARGET[0], TARGET[1], kb))


if __name__ == "__main__":
    main()
