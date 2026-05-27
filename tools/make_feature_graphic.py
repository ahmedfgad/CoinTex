"""Generate a Google Play feature graphic for CoinTex (1024x500).

Output: cointex_media/feature_graphic_1024x500.png
"""

from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1024, 500
OUT = os.path.join("cointex_media", "feature_graphic_1024x500.png")


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(c1, c2, t):
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def vertical_gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        c = lerp_rgb(top, bottom, y / max(1, h - 1))
        for x in range(w):
            px[x, y] = c
    return img


def radial_glow(size, color, alpha, center, radius):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    px = layer.load()
    cx, cy = center
    r2 = radius * radius
    for y in range(h):
        dy = y - cy
        for x in range(w):
            dx = x - cx
            d2 = dx * dx + dy * dy
            if d2 > r2:
                continue
            t = 1 - math.sqrt(d2) / radius
            a = int(alpha * (t ** 2))
            if a:
                px[x, y] = (color[0], color[1], color[2], a)
    return layer


def draw_coin(draw: ImageDraw.ImageDraw, cx, cy, r, gold=(255, 205, 60), edge=(195, 140, 20)):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=edge)
    draw.ellipse((cx - r + max(2, r // 6), cy - r + max(2, r // 6),
                  cx + r - max(2, r // 6), cy + r - max(2, r // 6)),
                 fill=gold)
    # five-point star
    points = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r * 0.55 if i % 2 == 0 else r * 0.23
        points.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(points, fill=edge)


def draw_player(canvas: Image.Image, cx, cy, r, body=(56, 145, 230)):
    """A round blue blob with eyes and beak, like the in-game PlayerSprite."""
    # soft shadow under
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((cx - r, cy + r - r // 3, cx + r, cy + r + r // 2),
                               fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=8))
    canvas.alpha_composite(sh)

    d = ImageDraw.Draw(canvas)
    # body
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=body + (255,))
    # belly highlight
    bl = tuple(min(255, int(body[i] + (255 - body[i]) * 0.35)) for i in range(3))
    d.ellipse((cx - r + r // 5, cy - r // 6, cx + r - r // 5, cy + r - r // 6), fill=bl + (255,))
    # eyes
    er = max(3, r // 5)
    ex = r // 3
    ey = -r // 5
    d.ellipse((cx - ex - er, cy + ey - er, cx - ex + er, cy + ey + er), fill=(255, 255, 255, 255))
    d.ellipse((cx + ex - er, cy + ey - er, cx + ex + er, cy + ey + er), fill=(255, 255, 255, 255))
    pr = max(2, er // 2)
    d.ellipse((cx - ex - pr, cy + ey - pr, cx - ex + pr, cy + ey + pr), fill=(20, 20, 30, 255))
    d.ellipse((cx + ex - pr, cy + ey - pr, cx + ex + pr, cy + ey + pr), fill=(20, 20, 30, 255))
    # beak
    bx, by = cx, cy + r // 4
    bw = r // 3
    d.polygon([(bx - bw, by), (bx + bw, by), (bx, by + bw)], fill=(255, 175, 50, 255))


def draw_monster(canvas: Image.Image, cx, cy, r):
    """Red chaser with bandit mask + alert mark, like in 05_combat_chasers.png."""
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((cx - r, cy + r - r // 3, cx + r, cy + r + r // 2),
                               fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=8))
    canvas.alpha_composite(sh)

    d = ImageDraw.Draw(canvas)
    # pulsing ring (subtle)
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14),
               outline=(255, 60, 60, 130), width=8)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=4))
    canvas.alpha_composite(glow)

    # body
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(210, 50, 50, 255))
    # bandit mask (dark band)
    bx0 = cx - r + r // 8
    bx1 = cx + r - r // 8
    by0 = cy - r // 5
    by1 = cy + r // 12
    d.rectangle((bx0, by0, bx1, by1), fill=(40, 40, 55, 255))
    # eyes inside mask
    er = max(3, r // 6)
    d.ellipse((cx - r // 3 - er, cy - er - 2, cx - r // 3 + er, cy + er - 2),
              fill=(255, 255, 255, 255))
    d.ellipse((cx + r // 3 - er, cy - er - 2, cx + r // 3 + er, cy + er - 2),
              fill=(255, 255, 255, 255))
    pr = max(2, er // 2)
    d.ellipse((cx - r // 3 - pr, cy - pr - 2, cx - r // 3 + pr, cy + pr - 2),
              fill=(20, 20, 30, 255))
    d.ellipse((cx + r // 3 - pr, cy - pr - 2, cx + r // 3 + pr, cy + pr - 2),
              fill=(20, 20, 30, 255))
    # frown
    fy = cy + r // 3
    d.arc((cx - r // 2, fy - r // 5, cx + r // 2, fy + r // 5),
          start=200, end=340, fill=(40, 40, 55, 255), width=4)


def draw_fire(canvas: Image.Image, cx, cy, r):
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i, (alpha, scale) in enumerate([(180, 1.8), (140, 1.4), (200, 1.0)]):
        rr = int(r * scale)
        gd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr),
                   fill=(255, 130, 40, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
    canvas.alpha_composite(glow)

    d = ImageDraw.Draw(canvas)
    # flame shape (simple)
    pts = []
    for i in range(20):
        ang = -math.pi / 2 + i * 2 * math.pi / 20
        wobble = 1.0 + 0.15 * math.sin(i * 1.7)
        rad = r * wobble
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=(255, 200, 60, 255))


def load_font(size, bold=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_text_with_shadow(img: Image.Image, xy, text, font, fill, shadow=(0, 0, 0, 160),
                          offset=(3, 4), blur=4):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0] + offset[0], xy[1] + offset[1]), text,
                               font=font, fill=shadow)
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur))
    img.alpha_composite(layer)
    ImageDraw.Draw(img).text(xy, text, font=font, fill=fill)


def main():
    random.seed(7)

    # Sky-to-deep-blue gradient (matches the in-game brand and the logo).
    bg = vertical_gradient((W, H), (88, 165, 240), (16, 50, 120)).convert("RGBA")

    # Big soft warm glow behind the title to lift the gold off the blue.
    bg.alpha_composite(radial_glow((W, H), (255, 200, 80), 90, (W * 0.42, H * 0.45), 380))
    # Subtle dark vignette at bottom corners.
    bg.alpha_composite(radial_glow((W, H), (0, 0, 0), 110, (0, H), 420))
    bg.alpha_composite(radial_glow((W, H), (0, 0, 0), 110, (W, H), 420))

    # Soft floating coin "bokeh" in the background.
    bokeh = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(28):
        x = random.randint(0, W)
        y = random.randint(0, H)
        r = random.randint(8, 22)
        a = random.randint(40, 90)
        bd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 210, 80, a))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(radius=8))
    bg.alpha_composite(bokeh)

    # Pick fonts first so we can measure and center the title.
    title_font = load_font(120, bold=True)
    sub_font = load_font(32, bold=True)
    tag_font = load_font(24, bold=False)

    title = "CoinTex"
    tagline = "Dodge monsters. Grab every coin."
    sub = "60 levels  |  6 worlds  |  2-player co-op or versus"

    # Measure title.
    tmp_draw = ImageDraw.Draw(bg)
    tb = tmp_draw.textbbox((0, 0), title, font=title_font)
    title_w = tb[2] - tb[0]
    title_h = tb[3] - tb[1]
    # Center the whole title block horizontally; sit it in the upper half.
    tx = (W - title_w) // 2
    ty = 60

    # Decorative scene tucked into the bottom-right corner, BELOW the title.
    draw_fire(bg, 950, 80, 22)
    draw_monster(bg, 925, 405, 55)
    draw_player(bg, 800, 425, 48)
    draw_coin(ImageDraw.Draw(bg), 870, 360, 14)

    # Small coin trail along the bottom-left, well clear of the text.
    trail = [
        (60, 430, 20),
        (135, 460, 18),
        (215, 440, 16),
        (300, 470, 14),
    ]
    for cx, cy, r in trail:
        draw_coin(ImageDraw.Draw(bg), cx, cy, r)

    # Large hero coin in the upper-left, balancing the right-side scene.
    draw_coin(ImageDraw.Draw(bg), 90, 130, 55)

    # Title with drop shadow + gold fill + top highlight.
    draw_text_with_shadow(bg, (tx, ty), title, title_font,
                          fill=(255, 215, 70, 255),
                          shadow=(0, 0, 0, 200), offset=(4, 6), blur=5)
    hl = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).text((tx, ty), title, font=title_font, fill=(255, 245, 170, 255))
    mask = Image.new("L", bg.size, 0)
    ImageDraw.Draw(mask).rectangle((0, 0, W, ty + title_h // 2), fill=180)
    bg.paste(hl, (0, 0), mask)

    # Tagline + sub, centered under the title.
    sb = tmp_draw.textbbox((0, 0), tagline, font=sub_font)
    tb2 = tmp_draw.textbbox((0, 0), sub, font=tag_font)
    sub_x = (W - (sb[2] - sb[0])) // 2
    tag_x = (W - (tb2[2] - tb2[0])) // 2
    sub_y = ty + title_h + 40
    tag_y = sub_y + (sb[3] - sb[1]) + 18

    draw_text_with_shadow(bg, (sub_x, sub_y), tagline, sub_font,
                          fill=(255, 255, 255, 255),
                          shadow=(0, 0, 0, 180), offset=(2, 3), blur=3)
    draw_text_with_shadow(bg, (tag_x, tag_y), sub, tag_font,
                          fill=(255, 230, 150, 255),
                          shadow=(0, 0, 0, 170), offset=(2, 3), blur=3)

    # Save as PNG (RGB; Play accepts PNG/JPEG with no alpha needed).
    final = bg.convert("RGB")
    os.makedirs("cointex_media", exist_ok=True)
    final.save(OUT, "PNG", optimize=True)

    size_kb = os.path.getsize(OUT) / 1024.0
    print("Wrote {}  ({:.1f} KB, {}x{})".format(OUT, size_kb, final.size[0], final.size[1]))


if __name__ == "__main__":
    main()
