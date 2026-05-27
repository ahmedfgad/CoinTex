"""Generate a YouTube thumbnail for the CoinTex promo video (1280x720).

Output: cointex_media/youtube_thumbnail_1280x720.png
"""

from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
OUT = os.path.join("cointex_media", "youtube_thumbnail_1280x720.png")


# --- shared helpers (kept in-file so the script is standalone) ---------------

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


def draw_coin(draw, cx, cy, r, gold=(255, 205, 60), edge=(195, 140, 20)):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=edge)
    inset = max(2, r // 6)
    draw.ellipse((cx - r + inset, cy - r + inset, cx + r - inset, cy + r - inset), fill=gold)
    points = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r * 0.55 if i % 2 == 0 else r * 0.23
        points.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(points, fill=edge)


def draw_player(canvas, cx, cy, r, body=(56, 145, 230), looking=1):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((cx - r, cy + r - r // 3, cx + r, cy + r + r // 2),
                               fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=10))
    canvas.alpha_composite(sh)

    d = ImageDraw.Draw(canvas)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=body + (255,))
    bl = tuple(min(255, int(body[i] + (255 - body[i]) * 0.35)) for i in range(3))
    d.ellipse((cx - r + r // 5, cy - r // 6, cx + r - r // 5, cy + r - r // 6), fill=bl + (255,))
    er = max(4, r // 5)
    ex = r // 3
    ey = -r // 5
    pr = max(3, er // 2)
    # both eyes look toward `looking` direction (-1 = left, +1 = right)
    pup_off = max(1, pr // 2) * looking
    d.ellipse((cx - ex - er, cy + ey - er, cx - ex + er, cy + ey + er), fill=(255, 255, 255, 255))
    d.ellipse((cx + ex - er, cy + ey - er, cx + ex + er, cy + ey + er), fill=(255, 255, 255, 255))
    d.ellipse((cx - ex - pr + pup_off, cy + ey - pr, cx - ex + pr + pup_off, cy + ey + pr),
              fill=(20, 20, 30, 255))
    d.ellipse((cx + ex - pr + pup_off, cy + ey - pr, cx + ex + pr + pup_off, cy + ey + pr),
              fill=(20, 20, 30, 255))
    bx, by = cx + (r // 6) * looking, cy + r // 4
    bw = r // 3
    d.polygon([(bx - bw, by), (bx + bw, by), (bx + (r // 4) * looking, by + bw)],
              fill=(255, 175, 50, 255))


def draw_monster(canvas, cx, cy, r):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((cx - r, cy + r - r // 3, cx + r, cy + r + r // 2),
                               fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=10))
    canvas.alpha_composite(sh)

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((cx - r - 18, cy - r - 18, cx + r + 18, cy + r + 18),
               outline=(255, 60, 60, 170), width=10)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
    canvas.alpha_composite(glow)

    d = ImageDraw.Draw(canvas)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(210, 50, 50, 255))
    bx0 = cx - r + r // 8
    bx1 = cx + r - r // 8
    by0 = cy - r // 5
    by1 = cy + r // 12
    d.rectangle((bx0, by0, bx1, by1), fill=(40, 40, 55, 255))
    er = max(3, r // 6)
    pr = max(2, er // 2)
    d.ellipse((cx - r // 3 - er, cy - er - 2, cx - r // 3 + er, cy + er - 2),
              fill=(255, 255, 255, 255))
    d.ellipse((cx + r // 3 - er, cy - er - 2, cx + r // 3 + er, cy + er - 2),
              fill=(255, 255, 255, 255))
    d.ellipse((cx - r // 3 - pr, cy - pr - 2, cx - r // 3 + pr, cy + pr - 2),
              fill=(20, 20, 30, 255))
    d.ellipse((cx + r // 3 - pr, cy - pr - 2, cx + r // 3 + pr, cy + pr - 2),
              fill=(20, 20, 30, 255))
    fy = cy + r // 3
    d.arc((cx - r // 2, fy - r // 5, cx + r // 2, fy + r // 5),
          start=200, end=340, fill=(40, 40, 55, 255), width=5)
    # "!" mark above
    mx, my = cx + r - r // 4, cy - r - r // 3
    d.rounded_rectangle((mx - r // 10, my, mx + r // 10, my + r // 2),
                        radius=r // 18, fill=(255, 230, 60, 255))
    d.ellipse((mx - r // 10, my + r // 2 + 4, mx + r // 10, my + r // 2 + 4 + r // 5),
              fill=(255, 230, 60, 255))


def draw_fire(canvas, cx, cy, r):
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for alpha, scale in [(200, 1.8), (160, 1.4), (220, 1.0)]:
        rr = int(r * scale)
        gd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 130, 40, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    canvas.alpha_composite(glow)
    d = ImageDraw.Draw(canvas)
    pts = []
    for i in range(24):
        ang = -math.pi / 2 + i * 2 * math.pi / 24
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


def text_with_shadow(img, xy, text, font, fill, shadow=(0, 0, 0, 180),
                     offset=(4, 6), blur=5):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0] + offset[0], xy[1] + offset[1]), text,
                               font=font, fill=shadow)
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur))
    img.alpha_composite(layer)
    ImageDraw.Draw(img).text(xy, text, font=font, fill=fill)


# --- composition -------------------------------------------------------------

def draw_motion_streaks(canvas, x0, y0, dx, count=4, length=120, color=(255, 255, 255, 160)):
    """Horizontal speed lines trailing behind a moving sprite."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(count):
        yy = y0 + (i - count // 2) * 14
        x_end = x0 - dx * (length + i * 20)
        d.line((x0, yy, x_end, yy), fill=color, width=6)
    layer = layer.filter(ImageFilter.GaussianBlur(radius=3))
    canvas.alpha_composite(layer)


def draw_badge(canvas, cx, cy, text, font, fill=(220, 50, 50, 255), text_fill=(255, 255, 255, 255)):
    """Tilted red ribbon badge."""
    bbox = ImageDraw.Draw(canvas).textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 26, 14
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    chip = Image.new("RGBA", (bw + 40, bh + 40), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chip)
    cd.rounded_rectangle((20, 20, 20 + bw, 20 + bh), radius=18, fill=fill)
    cd.text((20 + pad_x - bbox[0], 20 + pad_y - bbox[1]), text, font=font, fill=text_fill)
    chip = chip.rotate(-8, resample=Image.BICUBIC, expand=True)
    # drop shadow
    sh = Image.new("RGBA", chip.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle((20, 28, 20 + bw, 28 + bh), radius=18, fill=(0, 0, 0, 180))
    sh = sh.rotate(-8, resample=Image.BICUBIC, expand=True).filter(ImageFilter.GaussianBlur(8))
    paste_xy = (cx - chip.size[0] // 2, cy - chip.size[1] // 2)
    canvas.alpha_composite(sh, dest=paste_xy)
    canvas.alpha_composite(chip, dest=paste_xy)


def main():
    random.seed(11)

    # Deep blue gradient background.
    bg = vertical_gradient((W, H), (95, 175, 245), (12, 40, 100)).convert("RGBA")

    # Big warm glow behind the action.
    bg.alpha_composite(radial_glow((W, H), (255, 200, 80), 130, (W * 0.55, H * 0.62), 520))
    # Subtle dark vignette in the corners.
    bg.alpha_composite(radial_glow((W, H), (0, 0, 0), 130, (0, H), 600))
    bg.alpha_composite(radial_glow((W, H), (0, 0, 0), 130, (W, H), 600))
    bg.alpha_composite(radial_glow((W, H), (0, 0, 0), 90, (0, 0), 500))

    # Floating coin bokeh.
    bokeh = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(40):
        x = random.randint(0, W)
        y = random.randint(0, H)
        r = random.randint(10, 28)
        a = random.randint(40, 100)
        bd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 210, 80, a))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(radius=10))
    bg.alpha_composite(bokeh)

    # --- Action band along the bottom -------------------------------------
    # The blue player is fleeing left; a red chaser thunders in from the
    # right with a "!" alert. A fire hazard pulses above them. Coins scatter
    # across their path. Motion streaks sell the chase.
    fire_cx, fire_cy = 880, 410
    draw_fire(bg, fire_cx, fire_cy, 46)

    chaser_cx, chaser_cy = 1020, 555
    draw_motion_streaks(bg, chaser_cx - 110, chaser_cy + 10, dx=1, count=4, length=180,
                        color=(255, 80, 80, 130))
    draw_monster(bg, chaser_cx, chaser_cy, 110)

    player_cx, player_cy = 700, 575
    draw_motion_streaks(bg, player_cx + 90, player_cy + 10, dx=-1, count=4, length=170,
                        color=(180, 230, 255, 150))
    draw_player(bg, player_cx, player_cy, 90, looking=-1)

    # Coins strewn through the action zone.
    for cx, cy, r in [
        (340, 600, 26),
        (450, 560, 22),
        (560, 610, 24),
        (640, 660, 20),
        (820, 660, 24),
        (1180, 620, 22),
        (240, 660, 20),
        (130, 620, 24),
    ]:
        draw_coin(ImageDraw.Draw(bg), cx, cy, r)

    # Big hero coin upper-left.
    draw_coin(ImageDraw.Draw(bg), 130, 200, 80)

    # --- Title block ------------------------------------------------------
    title_font = load_font(200, bold=True)
    sub_font = load_font(56, bold=True)
    meta_font = load_font(36, bold=False)
    badge_font = load_font(38, bold=True)

    title = "CoinTex"
    sub = "Run.  Dodge.  Collect."
    meta = "60 levels   |   6 worlds   |   2-player co-op or versus"

    draw = ImageDraw.Draw(bg)
    tb = draw.textbbox((0, 0), title, font=title_font)
    title_w = tb[2] - tb[0]
    title_h = tb[3] - tb[1]
    tx = (W - title_w) // 2
    ty = 70

    # Title: thick black shadow + gold fill + top highlight (same recipe as the
    # feature graphic so the two pieces feel like the same brand).
    text_with_shadow(bg, (tx, ty), title, title_font,
                     fill=(255, 215, 70, 255),
                     shadow=(0, 0, 0, 210), offset=(6, 8), blur=6)
    hl = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).text((tx, ty), title, font=title_font, fill=(255, 245, 170, 255))
    mask = Image.new("L", bg.size, 0)
    ImageDraw.Draw(mask).rectangle((0, 0, W, ty + title_h // 2), fill=190)
    bg.paste(hl, (0, 0), mask)

    # Sub-tagline directly under the title.
    sb = draw.textbbox((0, 0), sub, font=sub_font)
    sub_x = (W - (sb[2] - sb[0])) // 2
    sub_y = ty + title_h + 30
    text_with_shadow(bg, (sub_x, sub_y), sub, sub_font,
                     fill=(255, 255, 255, 255),
                     shadow=(0, 0, 0, 200), offset=(3, 4), blur=4)

    # Meta line, dim gold, under the sub.
    mb = draw.textbbox((0, 0), meta, font=meta_font)
    meta_x = (W - (mb[2] - mb[0])) // 2
    meta_y = sub_y + (sb[3] - sb[1]) + 18
    text_with_shadow(bg, (meta_x, meta_y), meta, meta_font,
                     fill=(255, 230, 150, 255),
                     shadow=(0, 0, 0, 170), offset=(2, 3), blur=3)

    # Tilted "OPEN SOURCE" badge in the top-right corner.
    draw_badge(bg, 1130, 110, "OPEN SOURCE", badge_font)

    # Save.
    final = bg.convert("RGB")
    os.makedirs("cointex_media", exist_ok=True)
    final.save(OUT, "PNG", optimize=True)

    size_kb = os.path.getsize(OUT) / 1024.0
    print("Wrote {}  ({:.1f} KB, {}x{})".format(OUT, size_kb, final.size[0], final.size[1]))


if __name__ == "__main__":
    main()
