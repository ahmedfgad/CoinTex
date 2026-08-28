"""Create App Store screenshot sets for iPhone and iPad.

The checked-in captures are real 16:9 CoinTex screens. Each image is scaled to
fit without cropping or distortion, then its edge colours are extended into
any remaining area. Outputs are opaque RGB PNGs at exact App Store Connect
sizes supplied for this release.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

SOURCE = Path("cointex_media/tablet_screenshots")
DESTINATION = Path("app_store/screenshots")
TARGETS = {
    "iphone": (2688, 1242),
    "ipad": (2752, 2064),
}


def fit_with_extended_edges(screenshot: Image.Image,
                            target: tuple[int, int]) -> Image.Image:
    """Fit a screenshot inside target and extend its outermost pixels."""
    scale = min(target[0] / screenshot.width, target[1] / screenshot.height)
    size = (round(screenshot.width * scale), round(screenshot.height * scale))
    resized = screenshot.resize(size, Image.Resampling.LANCZOS)
    left = (target[0] - size[0]) // 2
    top = (target[1] - size[1]) // 2
    right = target[0] - size[0] - left
    bottom = target[1] - size[1] - top

    canvas = Image.new("RGB", target)
    canvas.paste(resized, (left, top))
    if left:
        edge = resized.crop((0, 0, 1, size[1])).resize((left, size[1]))
        canvas.paste(edge, (0, top))
    if right:
        edge = resized.crop((size[0] - 1, 0, size[0], size[1]))
        canvas.paste(edge.resize((right, size[1])), (left + size[0], top))
    if top:
        edge = canvas.crop((0, top, target[0], top + 1))
        canvas.paste(edge.resize((target[0], top)), (0, 0))
    if bottom:
        edge = canvas.crop((0, top + size[1] - 1,
                            target[0], top + size[1]))
        canvas.paste(edge.resize((target[0], bottom)),
                     (0, top + size[1]))
    return canvas


def main() -> None:
    sources = sorted(SOURCE.glob("*.png"))
    if not sources:
        raise SystemExit(f"No screenshots found in {SOURCE}")
    if len(sources) > 10:
        raise SystemExit("App Store screenshot sets cannot exceed 10 images")

    for device, target in TARGETS.items():
        destination = DESTINATION / device
        destination.mkdir(parents=True, exist_ok=True)
        for source in sources:
            with Image.open(source) as image:
                screenshot = image.convert("RGB")
            canvas = fit_with_extended_edges(screenshot, target)
            output = destination / source.name
            canvas.save(output, "PNG", optimize=True)
            print("{} -> {} ({}x{})".format(source, output, *target))


if __name__ == "__main__":
    main()
