# Renders every game sprite to PNG files for review (a labeled sheet plus one
# transparent PNG per sprite/direction/state). The game draws these in code;
# this is review only.
#   xvfb-run -a ./venv/bin/python tools/render_sprites.py [output_dir]

import os
import sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

import graphics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "sprite_preview")
DIRS = [("right", (1, 0)), ("up", (0, 1)), ("left", (-1, 0)), ("down", (0, -1))]
MONSTER_NAMES = {1: "imp", 2: "spiker", 3: "brute"}
MONSTER_LABELS = {1: "Imp (1 hit)", 2: "Spiker (2 hits)", 3: "Brute (3 hits)"}


class Sheet(App):
    def build(self):
        self.exports = []  # (sprite, filename) for individual export
        grid = GridLayout(cols=5, padding=20, spacing=12)
        with grid.canvas.before:
            Color(0.86, 0.88, 0.90, 1)
            self._bg = Rectangle()
        grid.bind(pos=lambda *a: setattr(self._bg, "pos", grid.pos),
                  size=lambda *a: setattr(self._bg, "size", grid.size))

        def add_cell(sprite, text, filename):
            box = BoxLayout(orientation="vertical")
            holder = FloatLayout()
            sprite.size_hint = (0.8, 0.8)
            sprite.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            holder.add_widget(sprite)
            box.add_widget(holder)
            box.add_widget(Label(text=text, size_hint_y=0.22, color=(0.1, 0.1, 0.1, 1), font_size="14sp"))
            grid.add_widget(box)
            self.exports.append((sprite, filename))

        for name, d in DIRS:
            s = graphics.PlayerSprite()
            s.face_x, s.face_y = d
            s.moving = True
            s.phase = 0.6
            add_cell(s, "Player " + name, "player_%s.png" % name)
        dead = graphics.PlayerSprite()
        dead.dead = True
        dead.phase = 0.6
        add_cell(dead, "Player dead", "player_dead.png")

        for mtype in (1, 2, 3):
            for name, d in DIRS:
                m = graphics.MonsterSprite()
                m.mtype = mtype
                m.max_hp = mtype
                m.hp = mtype
                m.face_x, m.face_y = d
                m.moving = True
                m.phase = 0.6
                add_cell(m, MONSTER_LABELS[mtype] + " " + name, "%s_%s.png" % (MONSTER_NAMES[mtype], name))
            grid.add_widget(Label(text=MONSTER_LABELS[mtype], color=(0.1, 0.1, 0.1, 1), bold=True))

        add_cell(graphics.Coin(), "Coin", "coin.png")
        hazard = graphics.Hazard()
        hazard.phase = 0.5
        add_cell(hazard, "Fire hazard", "fire.png")
        add_cell(graphics.Projectile(), "Projectile", "projectile.png")
        grid.add_widget(Label(text=""))
        grid.add_widget(Label(text=""))

        self.grid = grid
        Clock.schedule_once(self._shoot, 0.7)
        return grid

    def _shoot(self, dt):
        os.makedirs(OUT_DIR, exist_ok=True)
        self.grid.export_to_png(os.path.join(OUT_DIR, "sprite_sheet.png"))
        for sprite, filename in self.exports:
            sprite.export_to_png(os.path.join(OUT_DIR, filename))
        print("EXPORTED %d sprites plus the sheet to %s" % (len(self.exports), OUT_DIR))
        self.stop()


if __name__ == "__main__":
    Sheet().run()
