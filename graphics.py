# All of CoinTex's graphics are drawn here with the Kivy canvas. There are no
# image files. Each sprite is a Widget that paints shapes (circles, rectangles,
# lines) inside its own pos/size and animates by reading a "phase" value that a
# single shared clock keeps advancing.

import math
import random

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty, ListProperty, BooleanProperty
from kivy.graphics import Color, Ellipse, Rectangle, Line, Triangle
from kivy.clock import Clock


# One clock drives every animated sprite, so we do not start dozens of timers.
_anim_sprites = set()
_anim_event = None


def _global_tick(dt):
    for sprite in list(_anim_sprites):
        sprite._advance(dt)


def _register(sprite):
    global _anim_event
    _anim_sprites.add(sprite)
    if _anim_event is None:
        _anim_event = Clock.schedule_interval(_global_tick, 1 / 30.0)


def _unregister(sprite):
    global _anim_event
    _anim_sprites.discard(sprite)
    if not _anim_sprites and _anim_event is not None:
        _anim_event.cancel()
        _anim_event = None


def _dir_triangle(bx, by, dx, dy, length, half_width):
    # A triangle whose tip points along (dx, dy) from a base centered at (bx, by).
    tip_x, tip_y = bx + dx * length, by + dy * length
    px, py = -dy, dx
    Triangle(points=[tip_x, tip_y,
                     bx + px * half_width, by + py * half_width,
                     bx - px * half_width, by - py * half_width])


class CanvasSprite(Widget):
    # Base class: holds an animation phase, a hit-flash value and a facing
    # direction, and redraws whenever any of them (or size/position) change.
    phase = NumericProperty(0.0)
    flash = NumericProperty(0.0)
    face_x = NumericProperty(1.0)   # heading direction as a unit vector
    face_y = NumericProperty(0.0)
    moving = BooleanProperty(False)

    def __init__(self, anim_speed=1.0, **kwargs):
        super().__init__(**kwargs)
        self._anim_speed = anim_speed
        self.bind(pos=self._redraw, size=self._redraw, phase=self._redraw,
                  flash=self._redraw, face_x=self._redraw, face_y=self._redraw,
                  moving=self._redraw)
        self._redraw()

    def _facing(self):
        length = (self.face_x ** 2 + self.face_y ** 2) ** 0.5 or 1.0
        return self.face_x / length, self.face_y / length

    def start(self):
        _register(self)

    def stop(self):
        _unregister(self)

    def _advance(self, dt):
        self.phase = self.phase + dt * self._anim_speed
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 3.0)

    def hit_flash(self):
        self.flash = 1.0

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            self.draw()

    def draw(self):
        pass


class Coin(CanvasSprite):
    # A gold coin that looks like it is slowly spinning (its width pinches in).
    def draw(self):
        x, y = self.pos
        w, h = self.size
        cx = x + w / 2
        spin = abs(math.cos(self.phase * 3.0))
        half_w = max(w * 0.42 * spin, w * 0.08)
        Color(0, 0, 0, 0.18)
        Ellipse(pos=(cx - half_w, y + h * 0.04), size=(half_w * 2, h * 0.30))
        Color(0.80, 0.58, 0.10, 1)
        Ellipse(pos=(cx - half_w, y + h * 0.12), size=(half_w * 2, h * 0.76))
        Color(1.0, 0.84, 0.25, 1)
        Ellipse(pos=(cx - half_w * 0.72, y + h * 0.24),
                size=(half_w * 1.44, h * 0.52))
        Color(1, 1, 1, 0.65)
        Ellipse(pos=(cx - half_w * 0.30, y + h * 0.55),
                size=(max(half_w * 0.3, 1), h * 0.16))


class PlayerSprite(CanvasSprite):
    # A friendly creature with shading, ears, walking feet and a face that turns
    # to look where it is heading.
    dead = BooleanProperty(False)
    body_color = ListProperty([0.20, 0.62, 1.0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(dead=self._redraw, body_color=self._redraw)

    def draw(self):
        x, y = self.pos
        w, h = self.size
        r = min(w, h) * 0.40
        cx = x + w / 2
        bob = 0.0 if self.dead else math.sin(self.phase * 8.0) * r * 0.06 * (1.0 if self.moving else 0.4)
        cy = y + h / 2 + bob
        fx, fy = self._facing()
        px, py = -fy, fx  # perpendicular to facing
        col = (0.55, 0.55, 0.58) if self.dead else tuple(self.body_color)
        dark = (col[0] * 0.78, col[1] * 0.78, col[2] * 0.82)
        light = (min(col[0] + 0.28, 1), min(col[1] + 0.28, 1), min(col[2] + 0.28, 1))

        # shadow on the ground
        Color(0, 0, 0, 0.22)
        Ellipse(pos=(cx - r * 0.9, y + h * 0.03), size=(r * 1.8, r * 0.42))

        # feet that step while moving
        if not self.dead:
            swing = math.sin(self.phase * 11.0) * r * 0.28 * (1.0 if self.moving else 0.0)
            Color(0.12, 0.12, 0.16, 1)
            Ellipse(pos=(cx - r * 0.55 + swing - r * 0.18, cy - r - r * 0.05), size=(r * 0.36, r * 0.26))
            Ellipse(pos=(cx + r * 0.55 - swing - r * 0.18, cy - r - r * 0.05), size=(r * 0.36, r * 0.26))

        # ears
        Color(*dark)
        Triangle(points=[cx - r * 0.55, cy + r * 0.45, cx - r * 0.05, cy + r * 0.55, cx - r * 0.2, cy + r * 1.15])
        Triangle(points=[cx + r * 0.55, cy + r * 0.45, cx + r * 0.05, cy + r * 0.55, cx + r * 0.2, cy + r * 1.15])

        # body with simple shading
        Color(*col)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
        Color(*dark)
        Ellipse(pos=(cx - r * 0.85, cy - r), size=(r * 1.7, r * 0.85))
        Color(*light)
        Ellipse(pos=(cx - r * 0.5, cy - r * 0.7), size=(r * 1.0, r * 0.8))
        Color(1, 1, 1, 0.35)
        Ellipse(pos=(cx - r * 0.45, cy + r * 0.2), size=(r * 0.5, r * 0.38))

        # a little nose pointing the way it faces
        if not self.dead:
            Color(1.0, 0.82, 0.4, 1)
            _dir_triangle(cx + fx * r * 0.55, cy + fy * r * 0.15, fx, fy, r * 0.45, r * 0.2)

        # eyes look toward the heading
        eye_r = r * 0.30
        base_x, base_y = cx + fx * r * 0.16, cy + r * 0.2 + fy * r * 0.1
        for side in (-1, 1):
            ex = base_x + px * r * 0.42 * side
            ey = base_y + py * r * 0.42 * side
            Color(1, 1, 1, 1)
            Ellipse(pos=(ex - eye_r, ey - eye_r), size=(eye_r * 2, eye_r * 2))
            if self.dead:
                Color(0.1, 0.1, 0.1, 1)
                Line(points=[ex - eye_r * 0.6, ey - eye_r * 0.6, ex + eye_r * 0.6, ey + eye_r * 0.6], width=1.6)
                Line(points=[ex - eye_r * 0.6, ey + eye_r * 0.6, ex + eye_r * 0.6, ey - eye_r * 0.6], width=1.6)
            else:
                ppx, ppy = ex + fx * eye_r * 0.5, ey + fy * eye_r * 0.5
                Color(0.08, 0.08, 0.12, 1)
                Ellipse(pos=(ppx - eye_r * 0.55, ppy - eye_r * 0.55), size=(eye_r * 1.1, eye_r * 1.1))
                Color(1, 1, 1, 0.9)
                Ellipse(pos=(ppx - eye_r * 0.15, ppy + eye_r * 0.05), size=(eye_r * 0.32, eye_r * 0.32))

        if self.flash > 0:
            Color(1, 1, 1, self.flash * 0.7)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))


# Color and shape per monster type. Type number comes from the level data.
MONSTER_COLORS = {
    1: (0.90, 0.30, 0.30),
    2: (0.65, 0.35, 0.85),
    3: (0.35, 0.40, 0.50),
}


class MonsterSprite(CanvasSprite):
    mtype = NumericProperty(1)
    hp = NumericProperty(1)
    max_hp = NumericProperty(1)
    frozen = BooleanProperty(False)
    chasing = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(mtype=self._redraw, hp=self._redraw, max_hp=self._redraw,
                  frozen=self._redraw, chasing=self._redraw)

    def draw(self):
        x, y = self.pos
        w, h = self.size
        r = min(w, h) * 0.40
        cx = x + w / 2
        wob = math.sin(self.phase * 6.0) * r * 0.06
        cy = y + h / 2 + wob
        base = MONSTER_COLORS.get(int(self.mtype), MONSTER_COLORS[1])
        if self.chasing and not self.frozen:
            base = (1.0, 0.25, 0.2)   # whole body turns angry red while chasing
        dark = (base[0] * 0.6, base[1] * 0.6, base[2] * 0.6)
        fx, fy = self._facing()
        px, py = -fy, fx
        mt = int(self.mtype)

        # shadow
        Color(0, 0, 0, 0.22)
        Ellipse(pos=(cx - r * 0.9, y + h * 0.03), size=(r * 1.8, r * 0.42))

        # spikes (type 2) or horns (others) behind the head
        Color(*dark)
        if mt == 2:
            for i in range(-2, 3):
                sx = cx + i * r * 0.42
                Triangle(points=[sx - r * 0.16, cy + r * 0.45, sx + r * 0.16, cy + r * 0.45, sx, cy + r * 1.2])
        else:
            Triangle(points=[cx - r * 0.7, cy + r * 0.3, cx - r * 0.3, cy + r * 0.45, cx - r * 0.5, cy + r * 1.15])
            Triangle(points=[cx + r * 0.7, cy + r * 0.3, cx + r * 0.3, cy + r * 0.45, cx + r * 0.5, cy + r * 1.15])

        # body with shading
        Color(base[0], base[1], base[2], 1)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
        Color(*dark)
        Ellipse(pos=(cx - r * 0.85, cy - r), size=(r * 1.7, r * 0.8))
        if mt == 3:
            Color(0.22, 0.24, 0.30, 1)  # armor band on the tough one
            Rectangle(pos=(cx - r, cy - r * 0.22), size=(r * 2, r * 0.44))

        # eyes toward the heading, with angry brows
        eye_r = r * 0.24
        base_x, base_y = cx + fx * r * 0.14, cy + r * 0.18 + fy * r * 0.08
        for side in (-1, 1):
            ex = base_x + px * r * 0.40 * side
            ey = base_y + py * r * 0.40 * side
            Color(1, 1, 1, 1)
            Ellipse(pos=(ex - eye_r, ey - eye_r), size=(eye_r * 2, eye_r * 2))
            ppx, ppy = ex + fx * eye_r * 0.5, ey + fy * eye_r * 0.5
            Color(0.7, 0.0, 0.0, 1)
            Ellipse(pos=(ppx - eye_r * 0.5, ppy - eye_r * 0.5), size=(eye_r, eye_r))
            Color(0.08, 0.04, 0.04, 1)
            Line(points=[ex - eye_r, ey + eye_r * 1.1, ex + eye_r * 0.7, ey + eye_r * 0.4], width=2)

        # fanged mouth at the front
        mx, my = cx + fx * r * 0.1, cy - r * 0.4
        Color(0.1, 0.0, 0.0, 1)
        Ellipse(pos=(mx - r * 0.32, my - r * 0.13), size=(r * 0.64, r * 0.26))
        Color(1, 1, 1, 1)
        Triangle(points=[mx - r * 0.22, my + r * 0.1, mx - r * 0.06, my + r * 0.1, mx - r * 0.14, my - r * 0.08])
        Triangle(points=[mx + r * 0.22, my + r * 0.1, mx + r * 0.06, my + r * 0.1, mx + r * 0.14, my - r * 0.08])

        # hp dots above the head: one per hit needed, gold = remaining. Shown for
        # every monster (even one-hit ones) so the meaning is consistent.
        pip = r * 0.16
        total = self.max_hp * pip * 2.2
        start = cx - total / 2
        for i in range(int(self.max_hp)):
            Color(0.95, 0.85, 0.2, 1) if i < self.hp else Color(0.3, 0.3, 0.3, 1)
            Ellipse(pos=(start + i * pip * 2.2, cy + r * 1.25), size=(pip * 1.6, pip * 1.6))

        if self.frozen:
            # icy tint to show the monster is paused
            Color(0.6, 0.85, 1.0, 0.45)
            Ellipse(pos=(cx - r * 1.05, cy - r * 1.05), size=(r * 2.1, r * 2.1))
        elif self.chasing:
            # Strong "it is hunting you" look: a bold pulsing red ring plus an
            # exclamation mark above the head (the body is already tinted red).
            ring = r * (1.15 + 0.12 * (0.5 + 0.5 * math.sin(self.phase * 8.0)))
            Color(1.0, 0.15, 0.1, 0.95)
            Line(ellipse=(cx - ring, cy - ring, ring * 2, ring * 2), width=3)
            ex, ey = cx, cy + r * 1.45
            Color(1.0, 0.95, 0.2, 1)
            Rectangle(pos=(ex - r * 0.08, ey), size=(r * 0.16, r * 0.5))      # bar
            Ellipse(pos=(ex - r * 0.1, ey - r * 0.3), size=(r * 0.2, r * 0.2))  # dot

        if self.flash > 0:
            Color(1, 1, 1, self.flash * 0.85)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))


class Hazard(CanvasSprite):
    # A flickering flame used as a moving hazard. size_factor lets the flame
    # pulse bigger and smaller; the engine scales the hitbox by the same value.
    size_factor = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size_factor=self._redraw)

    def draw(self):
        x, y = self.pos
        w, h = self.size
        cx = x + w / 2
        sf = self.size_factor
        flick = (0.85 + 0.15 * math.sin(self.phase * 12.0)) * sf
        Color(0.95, 0.35, 0.10, 1)
        Triangle(points=[cx - w * 0.4 * sf, y, cx + w * 0.4 * sf, y,
                         cx, y + h * flick])
        Color(1.0, 0.65, 0.15, 1)
        Triangle(points=[cx - w * 0.26 * sf, y, cx + w * 0.26 * sf, y,
                         cx, y + h * 0.72 * flick])
        Color(1.0, 0.92, 0.45, 0.95)
        Triangle(points=[cx - w * 0.13 * sf, y, cx + w * 0.13 * sf, y,
                         cx, y + h * 0.42 * flick])


class Projectile(CanvasSprite):
    # A small glowing shot fired by the player.
    color = ListProperty([0.5, 0.9, 1.0])

    def draw(self):
        x, y = self.pos
        w, h = self.size
        cx, cy = x + w / 2, y + h / 2
        r = min(w, h) / 2
        Color(self.color[0], self.color[1], self.color[2], 0.35)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
        Color(self.color[0], self.color[1], self.color[2], 1)
        Ellipse(pos=(cx - r * 0.55, cy - r * 0.55), size=(r * 1.1, r * 1.1))
        Color(1, 1, 1, 0.9)
        Ellipse(pos=(cx - r * 0.25, cy - r * 0.25), size=(r * 0.5, r * 0.5))


class ParticleBurst(Widget):
    # A short burst of dots that fly outward and fade, then removes itself.
    def __init__(self, center, color=(1, 0.9, 0.3), count=14, on_done=None, **kwargs):
        super().__init__(**kwargs)
        self.color = color
        self.on_done = on_done
        self._life = 0.0
        self._max_life = 0.6
        self._parts = []
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(60, 220)
            self._parts.append([center[0], center[1],
                                math.cos(ang) * spd, math.sin(ang) * spd,
                                random.uniform(3, 7)])
        _register(self)

    def _advance(self, dt):
        self._life += dt
        for p in self._parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] -= 240 * dt  # gravity
        self._redraw()
        if self._life >= self._max_life:
            _unregister(self)
            if self.parent:
                self.parent.remove_widget(self)
            if self.on_done:
                self.on_done()

    def _redraw(self):
        fade = max(0.0, 1.0 - self._life / self._max_life)
        self.canvas.clear()
        with self.canvas:
            for p in self._parts:
                Color(self.color[0], self.color[1], self.color[2], fade)
                Ellipse(pos=(p[0] - p[4], p[1] - p[4]), size=(p[4] * 2, p[4] * 2))


class FloatingText(Widget):
    # A bold "+N" label that pops in, drifts up, and fades out — used as
    # coin-collect feedback. Rides the same shared 30fps tick as everything
    # else, and removes itself when done.
    def __init__(self, center, text, color=(1.0, 0.85, 0.25),
                 font_size=24.0, duration=1.0, rise=80.0, on_done=None, **kwargs):
        super().__init__(**kwargs)
        self._life = 0.0
        self._dur = float(duration)
        self._cx, self._cy = center
        self._rise = float(rise)
        self._base_fs = float(font_size)
        self.on_done = on_done
        self.label = Label(
            text="[b]{}[/b]".format(text), markup=True, bold=True,
            color=(color[0], color[1], color[2], 1.0),
            font_size=self._base_fs, halign="center", valign="middle",
            size_hint=(None, None), size=(200, 56),
        )
        self.label.bind(size=lambda l, *_: setattr(l, "text_size", l.size))
        self.label.center = (self._cx, self._cy)
        self.add_widget(self.label)
        _register(self)

    def _advance(self, dt):
        self._life += dt
        f = min(1.0, self._life / self._dur)
        self.label.center = (self._cx, self._cy + self._rise * f)
        # Quick scale-in pop over the first ~0.15s.
        pop = 0.7 + 0.3 * min(1.0, self._life / 0.15)
        self.label.font_size = self._base_fs * pop
        # Hold, then fade over the back half.
        self.label.opacity = 1.0 if f < 0.5 else max(0.0, 1.0 - (f - 0.5) / 0.5)
        if self._life >= self._dur:
            _unregister(self)
            if self.parent:
                self.parent.remove_widget(self)
            if self.on_done:
                self.on_done()


class Background(Widget):
    # A vertical gradient using the world's two theme colors, with a few faint
    # accent shapes so each world looks different.
    def __init__(self, theme, **kwargs):
        self.theme = theme
        self._motif_seed = random.random()
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def set_theme(self, theme):
        self.theme = theme
        self._redraw()

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        top = self.theme["top"]
        bottom = self.theme["bottom"]
        accent = self.theme["accent"]
        strips = 48
        self.canvas.clear()
        with self.canvas:
            for i in range(strips):
                t = i / (strips - 1)
                c = [bottom[j] + (top[j] - bottom[j]) * t for j in range(3)]
                Color(c[0], c[1], c[2], 1)
                Rectangle(pos=(x, y + h * i / strips), size=(w, h / strips + 1))
            # a few soft accent circles for texture
            rnd = random.Random(self._motif_seed)
            Color(accent[0], accent[1], accent[2], 0.08)
            for _ in range(7):
                r = rnd.uniform(w * 0.05, w * 0.18)
                px = x + rnd.uniform(0, w)
                py = y + rnd.uniform(0, h)
                Ellipse(pos=(px - r, py - r), size=(r * 2, r * 2))


class Freezer(CanvasSprite):
    # A rare pickup that freezes the monsters for a while when collected.
    def draw(self):
        x, y = self.pos
        w, h = self.size
        cx, cy = x + w / 2, y + h / 2
        r = min(w, h) * 0.42 * (0.9 + 0.1 * math.sin(self.phase * 4.0))
        Color(0, 0, 0, 0.18)
        Ellipse(pos=(cx - r, y + h * 0.04), size=(r * 2, r * 0.4))
        Color(0.30, 0.70, 1.0, 1)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
        Color(0.78, 0.93, 1.0, 1)
        Ellipse(pos=(cx - r * 0.7, cy - r * 0.7), size=(r * 1.4, r * 1.4))
        Color(1, 1, 1, 1)
        for k in range(3):
            ang = math.pi * k / 3
            dx, dy = math.cos(ang) * r * 0.7, math.sin(ang) * r * 0.7
            Line(points=[cx - dx, cy - dy, cx + dx, cy + dy], width=1.6)


class FreezeTimer(Widget):
    # A round countdown. The colored wedge shrinks clockwise and the number in the
    # middle shows the seconds left. Reused for the freeze pickup (blue) and the
    # gun reload (orange) by passing different colors.
    fraction = NumericProperty(1.0)
    seconds = NumericProperty(0.0)

    def __init__(self, wedge=(0.45, 0.80, 1.0), dark=(0.05, 0.16, 0.32), **kwargs):
        from kivy.uix.label import Label
        super().__init__(**kwargs)
        self._wedge = wedge
        self._dark = dark
        self.label = Label(text="", bold=True, color=(1, 1, 1, 1))
        self.add_widget(self.label)
        self.bind(pos=self._redraw, size=self._redraw,
                  fraction=self._redraw, seconds=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        cx, cy = x + w / 2, y + h / 2
        r = min(w, h) * 0.5
        dr, dg, db = self._dark
        wr, wg, wb = self._wedge
        self.canvas.before.clear()
        with self.canvas.before:
            Color(dr, dg, db, 0.9)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(wr, wg, wb, 1)
            Ellipse(pos=(cx - r * 0.92, cy - r * 0.92), size=(r * 1.84, r * 1.84),
                    angle_start=0, angle_end=360 * max(0.0, min(1.0, self.fraction)))
            Color(dr, dg, db, 1)
            Ellipse(pos=(cx - r * 0.6, cy - r * 0.6), size=(r * 1.2, r * 1.2))
        self.label.center = (cx, cy)
        self.label.font_size = r * 0.8
        self.label.text = str(int(math.ceil(self.seconds))) if self.seconds > 0 else ""


class RespawnMarker(Widget):
    # Marks the spot where a killed monster will return and counts down the time
    # left with a shrinking red ring and a number.
    fraction = NumericProperty(1.0)
    seconds = NumericProperty(0.0)

    def __init__(self, **kwargs):
        from kivy.uix.label import Label
        super().__init__(**kwargs)
        self.label = Label(text="", bold=True, color=(1, 1, 1, 0.9))
        self.add_widget(self.label)
        self.bind(pos=self._redraw, size=self._redraw,
                  fraction=self._redraw, seconds=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        cx, cy = x + w / 2, y + h / 2
        r = min(w, h) * 0.5
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.12, 0.05, 0.05, 0.5)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(0.95, 0.35, 0.30, 0.95)
            Ellipse(pos=(cx - r * 0.92, cy - r * 0.92), size=(r * 1.84, r * 1.84),
                    angle_start=0, angle_end=360 * max(0.0, min(1.0, self.fraction)))
            Color(0.12, 0.05, 0.05, 0.85)
            Ellipse(pos=(cx - r * 0.6, cy - r * 0.6), size=(r * 1.2, r * 1.2))
        self.label.center = (cx, cy)
        self.label.font_size = r * 0.85
        self.label.text = str(int(math.ceil(self.seconds))) if self.seconds > 0 else ""


def draw_star(cx, cy, outer, color):
    # Draw a filled 5-pointed star centered at (cx, cy) as a fan of triangles.
    inner = outer * 0.42
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rr = outer if i % 2 == 0 else inner
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    Color(*color)
    for i in range(10):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % 10]
        Triangle(points=[cx, cy, ax, ay, bx, by])


class StarRow(Widget):
    # Shows `total` stars, the first `earned` filled gold and the rest faint.
    earned = NumericProperty(0)
    total = NumericProperty(3)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, earned=self._redraw, total=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        n = max(1, int(self.total))
        slot = w / n
        outer = min(slot, h) * 0.46
        cy = y + h / 2
        self.canvas.before.clear()
        with self.canvas.before:
            for i in range(n):
                cx = x + slot * (i + 0.5)
                if i < self.earned:
                    draw_star(cx, cy, outer, (1.0, 0.85, 0.2, 1))     # earned
                    Color(0.7, 0.5, 0.0, 1)
                    Line(points=_star_outline(cx, cy, outer), width=1.2, close=True)
                else:
                    draw_star(cx, cy, outer, (1.0, 1.0, 1.0, 0.20))   # not earned


def _star_outline(cx, cy, outer):
    # Perimeter points of a 5-pointed star, for drawing an outline.
    inner = outer * 0.42
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rr = outer if i % 2 == 0 else inner
        pts += [cx + math.cos(ang) * rr, cy + math.sin(ang) * rr]
    return pts
