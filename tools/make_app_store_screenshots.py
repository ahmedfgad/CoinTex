"""Create Apple's 6.9-inch landscape screenshot set from CoinTex captures.

The game captures are 16:9. Current iPhones are wider, so this keeps every UI
element visible at its original aspect ratio and extends the edge colours into
the narrow side areas. Outputs are opaque RGB PNGs at Apple's accepted
2796x1290 landscape size.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


SOURCE = Path("cointex_media/tablet_screenshots")
DESTINATION = Path("app_store/screenshots/iphone_6_9")
TARGET = (2796, 1290)


def main() -> None:
    sources = sorted(SOURCE.glob("*.png"))
    if not sources:
        raise SystemExit("No screenshots found in {}".format(SOURCE))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    for source in sources:
        screenshot = Image.open(source).convert("RGB")
        width = round(screenshot.width * TARGET[1] / screenshot.height)
        resized = screenshot.resize((width, TARGET[1]), resampling)
        if width > TARGET[0]:
            raise SystemExit("{} is wider than the target".format(source))

        left = (TARGET[0] - width) // 2
        right = TARGET[0] - width - left
        canvas = Image.new("RGB", TARGET)
        if left:
            left_edge = resized.crop((0, 0, 1, TARGET[1]))
            canvas.paste(left_edge.resize((left, TARGET[1])), (0, 0))
        canvas.paste(resized, (left, 0))
        if right:
            right_edge = resized.crop((width - 1, 0, width, TARGET[1]))
            canvas.paste(right_edge.resize((right, TARGET[1])),
                         (left + width, 0))

        output = DESTINATION / source.name
        canvas.save(output, "PNG", optimize=True)
        print("{} -> {} ({}x{})".format(source, output, *TARGET))


if __name__ == "__main__":
    main()
