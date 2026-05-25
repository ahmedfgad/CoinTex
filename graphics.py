# All of CoinTex's graphics are drawn here with the Kivy canvas. There are no
# image files. Each sprite is a Widget that paints shapes (circles, rectangles,
# lines) inside its own pos/size and animates by reading a "phase" value that a
# single shared clock keeps advancing.

import math
import random

from kivy.uix.widget import Widget
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


class CanvasSprite(Widget):
    # Base class: holds an animation phase and a hit-flash value, and redraws
    # whenever they (or the size/position) change.
    phase = NumericProperty(0.0)
    flash = NumericProperty(0.0)

    def __init__(self, anim_speed=1.0, **kwargs):
        super().__init__(**kwargs)
        self._anim_speed = anim_speed
        self.bind(pos=self._redraw, size=self._redraw,
                  phase=self._redraw, flash=self._redraw)
        self._redraw()

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
    # A round friendly creature. It bobs while moving and flashes when hurt.
    dead = BooleanProperty(False)
    body_color = ListProperty([0.20, 0.62, 1.0])

    def draw(self):
        x, y = self.pos
        w, h = self.size
        radius = min(w, h) * 0.40
        bob = 0 if self.dead else math.sin(self.phase * 6.0) * h * 0.04
        cx = x + w / 2
        cy = y + h / 2 + bob

        Color(0, 0, 0, 0.20)
        Ellipse(pos=(cx - radius * 0.9, y + h * 0.04),
                size=(radius * 1.8, radius * 0.5))

        if self.dead:
            Color(0.55, 0.55, 0.58, 1)
        else:
            Color(self.body_color[0], self.body_color[1], self.body_color[2], 1)
        Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))

        # little feet
        Color(0.12, 0.12, 0.15, 1)
        foot = radius * 0.35
        Ellipse(pos=(cx - radius * 0.6, cy - radius - foot * 0.4),
                size=(foot, foot * 0.7))
        Ellipse(pos=(cx + radius * 0.6 - foot, cy - radius - foot * 0.4),
                size=(foot, foot * 0.7))

        eye_r = radius * 0.28
        eye_y = cy + radius * 0.15
        for sign in (-1, 1):
            ex = cx + sign * radius * 0.38
            Color(1, 1, 1, 1)
            Ellipse(pos=(ex - eye_r, eye_y - eye_r), size=(eye_r * 2, eye_r * 2))
            if self.dead:
                Color(0.1, 0.1, 0.1, 1)
                Line(points=[ex - eye_r * 0.6, eye_y - eye_r * 0.6,
                             ex + eye_r * 0.6, eye_y + eye_r * 0.6], width=1.5)
                Line(points=[ex - eye_r * 0.6, eye_y + eye_r * 0.6,
                             ex + eye_r * 0.6, eye_y - eye_r * 0.6], width=1.5)
            else:
                Color(0.1, 0.1, 0.15, 1)
                Ellipse(pos=(ex - eye_r * 0.5, eye_y - eye_r * 0.5),
                        size=(eye_r, eye_r))

        if self.flash > 0:
            Color(1, 1, 1, self.flash * 0.7)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))


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

    def draw(self):
        x, y = self.pos
        w, h = self.size
        radius = min(w, h) * 0.40
        wobble = math.sin(self.phase * 5.0) * radius * 0.08
        cx = x + w / 2
        cy = y + h / 2
        base = MONSTER_COLORS.get(int(self.mtype), MONSTER_COLORS[1])

        Color(0, 0, 0, 0.20)
        Ellipse(pos=(cx - radius * 0.9, y + h * 0.04),
                size=(radius * 1.8, radius * 0.5))

        Color(base[0], base[1], base[2], 1)
        if int(self.mtype) == 2:
            # spiky body
            spikes = 9
            pts = []
            for i in range(spikes * 2):
                ang = math.pi * i / spikes
                rr = radius * (1.0 if i % 2 == 0 else 0.65)
                pts.extend([cx + math.cos(ang) * rr, cy + math.sin(ang) * rr + wobble])
            Line(points=pts + pts[:2], width=2)
            Ellipse(pos=(cx - radius * 0.7, cy - radius * 0.7 + wobble),
                    size=(radius * 1.4, radius * 1.4))
        else:
            Ellipse(pos=(cx - radius, cy - radius + wobble),
                    size=(radius * 2, radius * 2))
            if int(self.mtype) == 3:
                # tougher monster gets a darker armor band
                Color(0, 0, 0, 0.25)
                Rectangle(pos=(cx - radius, cy - radius * 0.2 + wobble),
                          size=(radius * 2, radius * 0.4))

        # angry eyes
        eye_r = radius * 0.22
        for sign in (-1, 1):
            ex = cx + sign * radius * 0.35
            ey = cy + radius * 0.2 + wobble
            Color(1, 1, 1, 1)
            Ellipse(pos=(ex - eye_r, ey - eye_r), size=(eye_r * 2, eye_r * 2))
            Color(0.1, 0.0, 0.0, 1)
            Ellipse(pos=(ex - eye_r * 0.5, ey - eye_r * 0.5), size=(eye_r, eye_r))

        # hp pips above the monster when it can take more than one hit
        if self.max_hp > 1:
            pip = radius * 0.16
            total = self.max_hp * pip * 2.2
            start = cx - total / 2
            for i in range(int(self.max_hp)):
                Color(0.95, 0.85, 0.2, 1) if i < self.hp else Color(0.3, 0.3, 0.3, 1)
                Ellipse(pos=(start + i * pip * 2.2, cy + radius * 1.05),
                        size=(pip * 1.6, pip * 1.6))

        if self.flash > 0:
            Color(1, 1, 1, self.flash * 0.8)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))


class Hazard(CanvasSprite):
    # A flickering flame used as a moving hazard.
    def draw(self):
        x, y = self.pos
        w, h = self.size
        cx = x + w / 2
        flick = 0.85 + 0.15 * math.sin(self.phase * 12.0)
        Color(0.95, 0.35, 0.10, 1)
        Triangle(points=[cx - w * 0.4, y, cx + w * 0.4, y,
                         cx, y + h * flick])
        Color(1.0, 0.65, 0.15, 1)
        Triangle(points=[cx - w * 0.26, y, cx + w * 0.26, y,
                         cx, y + h * 0.72 * flick])
        Color(1.0, 0.92, 0.45, 0.95)
        Triangle(points=[cx - w * 0.13, y, cx + w * 0.13, y,
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
