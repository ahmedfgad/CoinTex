# Menu, navigation and settings screens, plus a few reusable widgets.
# Everything is drawn with the canvas / standard widgets, no image files.
# The actual gameplay screen lives in main.py.

import math
import random
import threading

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.slider import Slider
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse
from kivy.metrics import sp, dp
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, BooleanProperty

import graphics
import levels
import net

ABOUT_TEXT = (
    "CoinTex\n"
    "\n"
    "Move your character to collect every coin in a level while dodging "
    "monsters and fire. Tap the fire button to shoot the nearest monster. "
    "Clear all coins to finish the level and unlock the next one.\n"
    "\n"
    "There are 6 worlds with 10 levels each. The further you go, the more "
    "monsters and hazards you face.\n"
    "\n"
    "CoinTex is built 100% with Python using the Kivy framework. Every screen, "
    "all the graphics and the sound are made in code.\n"
    "\n"
    "Tap the Auto button during a level to let the game play itself. A small "
    "genetic algorithm takes over and steers to the coins while keeping clear of "
    "monsters and fire. Tap it again to take back control.\n"
    "\n"
    "Multiplayer lets two people play together over the network. One device "
    "hosts and shows its address, the other joins with it. You can team up to "
    "clear the coins together or compete to collect the most.\n"
    "\n"
    "Created by Ahmed Fawzy Gad.\n"
    "Email: ahmed.f.gad@gmail.com\n"
    "Source code: https://github.com/ahmedfgad/CoinTex"
)


def app():
    return App.get_running_app()


class StyledButton(ButtonBehavior, Label):
    bg = ListProperty([0.20, 0.55, 0.95, 1])

    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", sp(22))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("color", [1, 1, 1, 1])
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(*self.bg)
            self._rect = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._sync, size=self._sync, bg=self._sync_color)

    def _sync(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _sync_color(self, *args):
        self._color.rgba = self.bg

    def on_press(self):
        running = app()
        if running is not None and getattr(running, "audio", None):
            running.audio.play_sfx("click")
        self._color.rgba = [self.bg[0] * 0.8, self.bg[1] * 0.8, self.bg[2] * 0.8, self.bg[3]]

    def on_release(self):
        self._color.rgba = self.bg


class ConfirmDialog(ModalView):
    def __init__(self, message, on_yes, yes_text="Yes", no_text="No", on_no=None, **kwargs):
        super().__init__(size_hint=(0.75, 0.45), auto_dismiss=False, **kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(16))
        with box.canvas.before:
            Color(0.12, 0.14, 0.22, 0.98)
            self._bg = RoundedRectangle(radius=[dp(16)])
        box.bind(pos=lambda *a: setattr(self._bg, "pos", box.pos),
                 size=lambda *a: setattr(self._bg, "size", box.size))
        box.add_widget(Label(text=message, font_size=sp(20), halign="center",
                             valign="middle", color=[1, 1, 1, 1]))
        row = BoxLayout(orientation="horizontal", spacing=dp(16), size_hint_y=0.4)
        no_btn = StyledButton(text=no_text, bg=[0.45, 0.45, 0.5, 1])
        yes_btn = StyledButton(text=yes_text, bg=[0.85, 0.3, 0.3, 1])

        def cancel(*a):
            self.dismiss()
            if on_no:
                on_no()
        no_btn.bind(on_release=cancel)

        def confirm(*a):
            self.dismiss()
            on_yes()
        yes_btn.bind(on_release=confirm)
        row.add_widget(no_btn)
        row.add_widget(yes_btn)
        box.add_widget(row)
        self.add_widget(box)


class InfoDialog(ModalView):
    # A simple message box with a title, body, and one OK button. Used for the
    # heads-up messages shown before a new mechanic appears.
    def __init__(self, title, message, on_ok=None, ok_text="Got it", **kwargs):
        super().__init__(size_hint=(0.82, 0.5), auto_dismiss=False, **kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(14))
        with box.canvas.before:
            Color(0.12, 0.14, 0.22, 0.98)
            self._bg = RoundedRectangle(radius=[dp(16)])
        box.bind(pos=lambda *a: setattr(self._bg, "pos", box.pos),
                 size=lambda *a: setattr(self._bg, "size", box.size))
        box.add_widget(Label(text=title, font_size=sp(28), bold=True,
                             color=[1, 0.85, 0.2, 1], size_hint_y=0.3))
        body = Label(text=message, font_size=sp(19), halign="center", valign="middle",
                     color=[1, 1, 1, 1], size_hint_y=0.48)
        body.bind(width=lambda *a: setattr(body, "text_size", (body.width, None)))
        box.add_widget(body)
        ok = StyledButton(text=ok_text, bg=[0.2, 0.7, 0.4, 1], size_hint_y=0.22)

        def confirm(*a):
            self.dismiss()
            if on_ok:
                on_ok()
        ok.bind(on_release=confirm)
        box.add_widget(ok)
        self.add_widget(box)


class StyledScreen(Screen):
    # A screen with a themed gradient background drawn in code.
    theme_world = 6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root_layout = FloatLayout()
        self.bg = graphics.Background(levels.get_world(self.theme_world), size_hint=(1, 1))
        self.root_layout.add_widget(self.bg)
        self.add_widget(self.root_layout)
        self.build()

    def build(self):
        pass


class MenuScreen(StyledScreen):
    def build(self):
        box = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(20),
                        size_hint=(0.7, 0.8), pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="CoinTex", font_size=sp(60), bold=True,
                             color=[1, 0.85, 0.2, 1], size_hint_y=0.4))
        play = StyledButton(text="Play", bg=[0.2, 0.7, 0.4, 1])
        multiplayer = StyledButton(text="Multiplayer", bg=[0.55, 0.4, 0.8, 1])
        how = StyledButton(text="How to play", bg=[0.9, 0.6, 0.2, 1])
        guide = StyledButton(text="Guide", bg=[0.85, 0.5, 0.25, 1])
        about = StyledButton(text="About", bg=[0.25, 0.5, 0.9, 1])
        settings = StyledButton(text="Settings", bg=[0.4, 0.45, 0.55, 1])
        play.bind(on_release=lambda *a: app().go("worldmap"))
        multiplayer.bind(on_release=lambda *a: app().go("multiplayer"))
        how.bind(on_release=lambda *a: app().go("tutorial"))
        guide.bind(on_release=lambda *a: app().go("guide"))
        about.bind(on_release=lambda *a: app().go("about"))
        settings.bind(on_release=lambda *a: app().go("settings"))
        box.add_widget(play)
        box.add_widget(multiplayer)
        box.add_widget(how)
        box.add_widget(guide)
        box.add_widget(about)
        box.add_widget(settings)
        self.stars = Label(text="", font_size=sp(18), color=[1, 1, 1, 0.85], size_hint_y=0.2)
        box.add_widget(self.stars)
        self.root_layout.add_widget(box)

    def on_enter(self):
        running = app()
        running.audio.play_menu_music()
        self.stars.text = "Stars collected: {}".format(running.state.total_stars())
        # The very first time the game is opened, run the tutorial automatically.
        if not running.state.get_setting("tutorial_seen"):
            Clock.schedule_once(lambda dt: running.go("tutorial"), 0)


class WorldMapScreen(StyledScreen):
    def build(self):
        outer = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        outer.add_widget(Label(text="Select World", font_size=sp(34), bold=True,
                              size_hint_y=0.15, color=[1, 1, 1, 1]))
        self.grid = GridLayout(cols=3, spacing=dp(16), size_hint_y=0.7)
        outer.add_widget(self.grid)
        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.15)
        back.bind(on_release=lambda *a: app().go("menu"))
        outer.add_widget(back)
        self.root_layout.add_widget(outer)

    def on_enter(self):
        running = app()
        running.audio.play_menu_music()
        self.grid.clear_widgets()
        for world in range(1, levels.NUM_WORLDS + 1):
            theme = levels.get_world(world)
            first_level = (world - 1) * levels.LEVELS_PER_WORLD + 1
            unlocked = running.state.is_unlocked(first_level)
            label = theme["name"] if unlocked else "Locked"
            color = [theme["top"][0], theme["top"][1], theme["top"][2], 1] if unlocked else [0.3, 0.3, 0.35, 1]
            btn = StyledButton(text="{}\n{}".format(world, label), bg=color, halign="center")
            if unlocked:
                btn.bind(on_release=lambda b, w=world: app().open_world(w))
            self.grid.add_widget(btn)


class LevelSelectScreen(StyledScreen):
    def build(self):
        self.outer = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        self.title = Label(text="", font_size=sp(30), bold=True, size_hint_y=0.14, color=[1, 1, 1, 1])
        self.outer.add_widget(self.title)
        self.grid = GridLayout(cols=5, spacing=dp(12), size_hint_y=0.72)
        self.outer.add_widget(self.grid)
        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.14)
        back.bind(on_release=lambda *a: app().go("worldmap"))
        self.outer.add_widget(back)
        self.root_layout.add_widget(self.outer)

    def on_enter(self):
        running = app()
        running.audio.play_menu_music()
        world = running.current_world
        theme = levels.get_world(world)
        self.title.text = "World {}  -  {}".format(world, theme["name"])
        self.bg.set_theme(theme)
        self.grid.clear_widgets()
        for lvl in levels.levels_in_world(world):
            index = lvl["index"]
            unlocked = running.state.is_unlocked(index)
            stars = running.state.get_stars(index)
            # Show the world and level number on every button, locked or not, and
            # draw real stars for the rating instead of asterisks.
            label = "W{} L{}".format(lvl["world"], lvl["world_index"])
            if unlocked:
                btn = LevelButton(text=label, bg=[0.25, 0.55, 0.9, 1])
                btn.stars = stars
                btn.bind(on_release=lambda b, i=index: running.start_level(i))
            else:
                btn = StyledButton(text=label + "\nLocked", bg=[0.3, 0.3, 0.35, 1], halign="center")
            self.grid.add_widget(btn)


class SettingsScreen(StyledScreen):
    def build(self):
        box = BoxLayout(orientation="vertical", padding=dp(26), spacing=dp(16),
                        size_hint=(0.8, 0.9), pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="Settings", font_size=sp(34), bold=True,
                             size_hint_y=0.12, color=[1, 1, 1, 1]))

        self.music_btn = StyledButton(size_hint_y=0.12)
        self.music_btn.bind(on_release=lambda *a: self._toggle("music_on", self.music_btn, "Music"))
        box.add_widget(self.music_btn)

        self.sfx_btn = StyledButton(size_hint_y=0.12)
        self.sfx_btn.bind(on_release=lambda *a: self._toggle("sfx_on", self.sfx_btn, "Sound effects"))
        box.add_widget(self.sfx_btn)

        vol_row = BoxLayout(orientation="horizontal", size_hint_y=0.12, spacing=dp(10))
        vol_row.add_widget(Label(text="Volume", font_size=sp(20), size_hint_x=0.35, color=[1, 1, 1, 1]))
        self.volume = Slider(min=0, max=1, value=1, step=0.05, size_hint_x=0.65)
        self.volume.bind(value=self._on_volume)
        vol_row.add_widget(self.volume)
        box.add_widget(vol_row)

        auto = StyledButton(text="Auto Player", bg=[0.3, 0.6, 0.55, 1], size_hint_y=0.12)
        auto.bind(on_release=lambda *a: app().go("autoplayer"))
        box.add_widget(auto)

        reset = StyledButton(text="Reset progress", bg=[0.85, 0.35, 0.3, 1], size_hint_y=0.12)
        reset.bind(on_release=lambda *a: self._confirm_reset())
        box.add_widget(reset)

        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.12)
        back.bind(on_release=lambda *a: app().go("menu"))
        box.add_widget(back)
        self.root_layout.add_widget(box)

    def on_enter(self):
        running = app()
        running.audio.play_menu_music()
        self.volume.value = running.state.get_setting("volume")
        self._refresh_labels()

    def _refresh_labels(self):
        running = app()
        on = running.state.get_setting("music_on")
        self.music_btn.text = "Music: {}".format("On" if on else "Off")
        self.music_btn.bg = [0.2, 0.7, 0.4, 1] if on else [0.5, 0.5, 0.55, 1]
        on = running.state.get_setting("sfx_on")
        self.sfx_btn.text = "Sound effects: {}".format("On" if on else "Off")
        self.sfx_btn.bg = [0.2, 0.7, 0.4, 1] if on else [0.5, 0.5, 0.55, 1]

    def _toggle(self, key, button, label):
        running = app()
        new_value = not running.state.get_setting(key)
        running.state.set_setting(key, new_value)
        running.audio.apply_settings()
        self._refresh_labels()

    def _on_volume(self, slider, value):
        running = app()
        running.state.set_setting("volume", round(value, 2))
        running.audio.apply_settings()

    def _confirm_reset(self):
        def do_reset():
            running = app()
            running.state.reset_progress()
            running.audio.apply_settings()
        ConfirmDialog("Reset all progress?\nThis cannot be undone.", do_reset,
                     yes_text="Reset", no_text="Cancel").open()


class AboutScreen(StyledScreen):
    def build(self):
        outer = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14))
        outer.add_widget(Label(text="About", font_size=sp(34), bold=True,
                              size_hint_y=0.12, color=[1, 1, 1, 1]))
        scroll = ScrollView(size_hint_y=0.74)
        text = Label(text=ABOUT_TEXT, font_size=sp(20), color=[1, 1, 1, 1],
                     halign="left", valign="top", padding=(dp(8), dp(8)))
        text.bind(width=lambda *a: setattr(text, "text_size", (text.width, None)))
        text.bind(texture_size=lambda *a: setattr(text, "height", text.texture_size[1]))
        text.size_hint_y = None
        scroll.add_widget(text)
        outer.add_widget(scroll)
        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.14)
        back.bind(on_release=lambda *a: app().go("menu"))
        outer.add_widget(back)
        self.root_layout.add_widget(outer)

    def on_enter(self):
        app().audio.play_menu_music()


class GunButton(ButtonBehavior, Widget):
    # The fire control, drawn as a blaster. Remaining ammo shows as bullet pips,
    # and it greys out while on cooldown or out of ammo. While the gun is
    # reloading, a countdown ring and a number are drawn on the button itself.
    ammo = NumericProperty(0)
    ready = BooleanProperty(True)
    reloading = BooleanProperty(False)
    reload_fraction = NumericProperty(0.0)
    reload_seconds = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reload_label = Label(text="", bold=True, color=(1, 1, 1, 1))
        self.add_widget(self._reload_label)
        self.bind(pos=self._redraw, size=self._redraw, ammo=self._redraw, ready=self._redraw,
                  reloading=self._redraw, reload_fraction=self._redraw, reload_seconds=self._redraw)
        self._redraw()

    def on_press(self):
        running = app()
        if running is not None and getattr(running, "audio", None):
            running.audio.play_sfx("click")

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        enabled = self.ready and self.ammo > 0 and not self.reloading
        self.canvas.before.clear()
        with self.canvas.before:
            if enabled:
                Color(0.90, 0.45, 0.18, 0.95)
            else:
                Color(0.40, 0.40, 0.45, 0.55)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
            gun = (1, 1, 1, 1) if enabled else (0.75, 0.75, 0.78, 0.6)
            Color(*gun)
            bx, by = x + w * 0.20, y + h * 0.46
            Rectangle(pos=(bx, by), size=(w * 0.42, h * 0.20))                       # body
            Rectangle(pos=(bx + w * 0.40, by + h * 0.04), size=(w * 0.26, h * 0.12))  # barrel
            Rectangle(pos=(bx + w * 0.06, by - h * 0.22), size=(w * 0.14, h * 0.24))  # grip
            count = max(0, int(self.ammo))
            pip_w = w * 0.11
            gap = w * 0.03
            total = count * pip_w + max(0, count - 1) * gap
            start = x + (w - total) / 2
            for i in range(count):
                Color(1, 0.9, 0.3, 1)
                Rectangle(pos=(start + i * (pip_w + gap), y + h * 0.12), size=(pip_w, h * 0.10))
            if self.reloading:
                # countdown ring + seconds drawn over the gun, so it clearly
                # belongs to the gun (not a separate respawn-looking marker).
                cx, cy = x + w / 2, y + h / 2
                r = min(w, h) * 0.34
                Color(0.0, 0.0, 0.0, 0.45)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
                Color(0.30, 0.15, 0.05, 0.95)
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                Color(1.0, 0.6, 0.2, 1)
                Ellipse(pos=(cx - r * 0.92, cy - r * 0.92), size=(r * 1.84, r * 1.84),
                        angle_start=0, angle_end=360 * max(0.0, min(1.0, self.reload_fraction)))
                Color(0.30, 0.15, 0.05, 1)
                Ellipse(pos=(cx - r * 0.55, cy - r * 0.55), size=(r * 1.1, r * 1.1))
        if self.reloading:
            self._reload_label.center = (x + w / 2, y + h / 2)
            self._reload_label.font_size = min(w, h) * 0.30
            self._reload_label.text = (str(int(math.ceil(self.reload_seconds)))
                                       if self.reload_seconds > 0 else "")
        else:
            self._reload_label.text = ""


class LevelButton(StyledButton):
    # A level tile that shows its label at the top and a real 3-star rating drawn
    # at the bottom (gold for earned stars, faint for the rest).
    stars = NumericProperty(0)

    def __init__(self, **kwargs):
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "top")
        super().__init__(**kwargs)
        self.bind(stars=self._draw_stars, pos=self._draw_stars, size=self._on_size)
        self._on_size()

    def _on_size(self, *args):
        self.text_size = (self.width, self.height)
        self._draw_stars()

    def _draw_stars(self, *args):
        self.canvas.after.clear()
        if self.width <= 1:
            return
        x, y = self.pos
        w, h = self.size
        slot = w * 0.24
        outer = slot * 0.40
        start = x + (w - slot * 3) / 2
        cy = y + h * 0.18
        with self.canvas.after:
            for i in range(3):
                cx = start + slot * (i + 0.5)
                color = (1.0, 0.85, 0.2, 1) if i < self.stars else (1.0, 1.0, 1.0, 0.22)
                graphics.draw_star(cx, cy, outer, color)


# Movement speed for the practice character. Slower than the real game so a new
# player can follow what is happening.
TUTORIAL_SPEED = 0.5


class TutorialScreen(StyledScreen):
    # A short hands-on tutorial. It does not use the real game screen; it runs a
    # small, forgiving practice level with step-by-step coaching. Reached from the
    # menu and shown automatically the first time the game is opened.
    theme_world = 1

    def build(self):
        self.health = 100.0
        self.step = 0
        self.world = FloatLayout()
        self.root_layout.add_widget(self.world)

        self.coach = Label(text="", font_size=sp(22), bold=True, color=[1, 1, 1, 1],
                           halign="center", valign="middle",
                           size_hint=(0.92, 0.18), pos_hint={"center_x": 0.5, "top": 0.99})
        self.coach.bind(width=lambda *a: setattr(self.coach, "text_size", (self.coach.width, None)))
        self.root_layout.add_widget(self.coach)

        # a demo health bar, shown when health is introduced
        self.health_holder = FloatLayout(size_hint=(0.3, 0.035), pos_hint={"x": 0.03, "top": 0.80})
        with self.health_holder.canvas.before:
            Color(0, 0, 0, 0.4)
            self._hp_bg = Rectangle()
            self._hp_color = Color(0.2, 0.8, 0.3, 1)
            self._hp_bar = Rectangle()
        self.health_holder.bind(pos=self._sync_hp, size=self._sync_hp)
        self.health_holder.opacity = 0
        self.root_layout.add_widget(self.health_holder)

        self.gun_btn = GunButton(size_hint=(0.17, 0.13), pos_hint={"right": 0.98, "y": 0.03})
        self.gun_btn.bind(on_release=lambda *a: self._fire())
        self.gun_btn.opacity = 0
        self.root_layout.add_widget(self.gun_btn)

        skip = StyledButton(text="Skip", bg=[0.45, 0.45, 0.5, 1], font_size=sp(16),
                            size_hint=(0.16, 0.08), pos_hint={"x": 0.02, "y": 0.03})
        skip.bind(on_release=lambda *a: self._finish())
        self.root_layout.add_widget(skip)

        self.player = self.coin = self.monster = self.hazard = None
        self._done_btn = None
        self._event = None

    # ----- lifecycle -----
    def on_enter(self):
        app().audio.play_menu_music()
        self._reset()
        if self._event is None:
            self._event = Clock.schedule_interval(self._update, 1 / 60.0)

    def on_leave(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self._clear()

    def _reset(self):
        self._clear()
        self.health = 100.0
        self.player = graphics.PlayerSprite(size_hint=(0.10, 0.14))
        self.player.cx, self.player.cy = 0.5, 0.4
        self.player.tx, self.player.ty = 0.5, 0.4
        self._origin = (0.5, 0.4)
        self._place(self.player)
        self.world.add_widget(self.player)
        self.player.start()
        self.health_holder.opacity = 0
        self.gun_btn.opacity = 0
        self._sync_hp()
        self._set_step(0)

    def _clear(self):
        for sprite in (self.player, self.coin, self.monster, self.hazard):
            if sprite is not None:
                sprite.stop()
                if sprite.parent:
                    sprite.parent.remove_widget(sprite)
        self.player = self.coin = self.monster = self.hazard = None
        if self._done_btn is not None:
            if self._done_btn.parent:
                self._done_btn.parent.remove_widget(self._done_btn)
            self._done_btn = None

    # ----- steps -----
    def _set_step(self, n):
        self.step = n
        self._step_t = 0.0
        if n == 0:
            self.coach.text = "Welcome! Tap anywhere on the screen to move your character."
        elif n == 1:
            self.coach.text = "Nice! Now move onto the coin to collect it."
            self._spawn_coin()
        elif n == 2:
            self.coach.text = ("Careful! Touching a monster or fire drains your health.\n"
                               "Keep your distance and watch the health bar.")
            self._damaged = False
            self._spawn_monster()
            self._spawn_hazard()
            self.health_holder.opacity = 1
        elif n == 3:
            self.coach.text = ("Tap the gun button (bottom right) to shoot. It automatically\n"
                               "hits the nearest monster, so you never need to aim.")
            self.gun_btn.ammo = 1
            self.gun_btn.ready = True
            self.gun_btn.opacity = 1
        elif n == 4:
            self.coach.text = ("That is it! In a real level, collect every coin before the\n"
                               "timer runs out. You are ready to play!")
            self.gun_btn.opacity = 0
            self._show_done()

    def _update(self, dt):
        if self.player is None:
            return
        self._move(self.player, self.player.tx, self.player.ty, TUTORIAL_SPEED * dt)

        if self.step == 0:
            ox, oy = self._origin
            if ((self.player.cx - ox) ** 2 + (self.player.cy - oy) ** 2) ** 0.5 > 0.12:
                self._set_step(1)
        elif self.step == 1:
            if self.coin is not None and self._touch(self.player, self.coin, 0.07):
                app().audio.play_sfx("coin")
                self.coin.stop()
                self.world.remove_widget(self.coin)
                self.coin = None
                self._set_step(2)
        elif self.step == 2:
            self._wander(self.monster, dt)
            self._sweep(self.hazard, dt)
            hit = ((self.monster is not None and self._touch(self.player, self.monster, 0.09))
                   or (self.hazard is not None and self._touch(self.player, self.hazard, 0.08)))
            if hit:
                self.health = max(25.0, self.health - 30.0 * dt)
                self.player.hit_flash()
                self._damaged = True
            self._update_hp_bar()
            self._step_t += dt
            if (self._damaged and self._step_t > 1.5) or self._step_t > 10.0:
                self._set_step(3)
        elif self.step == 3:
            self._wander(self.monster, dt)
            self._sweep(self.hazard, dt)

    def _fire(self):
        if self.step != 3 or self.monster is None:
            return
        running = app()
        running.audio.play_sfx("shoot")
        self.world.add_widget(graphics.ParticleBurst(self._px(self.monster), color=(1, 0.4, 0.4)))
        self.monster.stop()
        if self.monster.parent:
            self.monster.parent.remove_widget(self.monster)
        self.monster = None
        running.audio.play_sfx("monster_death")
        self._set_step(4)

    def _show_done(self):
        if self._done_btn is not None:
            return
        self._done_btn = StyledButton(text="Play!", bg=[0.2, 0.7, 0.4, 1],
                                      size_hint=(0.3, 0.1), pos_hint={"center_x": 0.5, "y": 0.16})
        self._done_btn.bind(on_release=lambda *a: self._finish())
        self.root_layout.add_widget(self._done_btn)

    def _finish(self):
        running = app()
        running.state.set_setting("tutorial_seen", True)
        running.go("menu")

    # ----- input -----
    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if self.player is not None:
            self.player.tx = min(max(touch.sx, 0.06), 0.94)
            self.player.ty = min(max(touch.sy, 0.10), 0.92)
            return True
        return False

    # ----- helpers (a small, self-contained copy of the game movement) -----
    def _place(self, sprite):
        shw, shh = sprite.size_hint
        sprite.pos_hint = {"x": sprite.cx - shw / 2, "y": sprite.cy - shh / 2}

    def _move(self, sprite, tx, ty, step):
        dx, dy = tx - sprite.cx, ty - sprite.cy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= step or dist == 0:
            sprite.cx, sprite.cy = tx, ty
            sprite.moving = False
            self._place(sprite)
            return True
        ux, uy = dx / dist, dy / dist
        sprite.face_x, sprite.face_y = ux, uy
        sprite.moving = True
        sprite.cx += ux * step
        sprite.cy += uy * step
        self._place(sprite)
        return False

    def _wander(self, monster, dt):
        if monster is None:
            return
        if self._move(monster, monster.tx, monster.ty, 0.18 * dt):
            monster.tx = random.uniform(0.2, 0.8)
            monster.ty = random.uniform(0.3, 0.7)

    def _sweep(self, hazard, dt):
        if hazard is None:
            return
        hazard.t = (hazard.t + dt / hazard.period) % 1.0
        phase = 0.5 - 0.5 * math.cos(hazard.t * 2 * math.pi)
        hazard.cx = hazard.ax + (hazard.bx - hazard.ax) * phase
        hazard.cy = hazard.ay + (hazard.by - hazard.ay) * phase
        self._place(hazard)

    def _touch(self, a, b, thresh):
        return ((a.cx - b.cx) ** 2 + (a.cy - b.cy) ** 2) ** 0.5 < thresh

    def _px(self, sprite):
        return (self.world.x + sprite.cx * self.world.width,
                self.world.y + sprite.cy * self.world.height)

    def _spawn_coin(self):
        self.coin = graphics.Coin(size_hint=(0.045, 0.06))
        self.coin.cx, self.coin.cy = 0.75, 0.55
        self._place(self.coin)
        self.world.add_widget(self.coin)
        self.coin.start()

    def _spawn_monster(self):
        self.monster = graphics.MonsterSprite(size_hint=(0.11, 0.14))
        self.monster.mtype = 1
        self.monster.max_hp = 1
        self.monster.hp = 1
        self.monster.cx, self.monster.cy = 0.25, 0.6
        self.monster.tx, self.monster.ty = 0.5, 0.5
        self._place(self.monster)
        self.world.add_widget(self.monster)
        self.monster.start()

    def _spawn_hazard(self):
        self.hazard = graphics.Hazard(size_hint=(0.05, 0.08))
        self.hazard.ax, self.hazard.ay = 0.4, 0.2
        self.hazard.bx, self.hazard.by = 0.4, 0.7
        self.hazard.t = 0.0
        self.hazard.period = 4.0
        self.hazard.size_factor = 1.0
        self.hazard.cx, self.hazard.cy = self.hazard.ax, self.hazard.ay
        self._place(self.hazard)
        self.world.add_widget(self.hazard)
        self.hazard.start()

    def _sync_hp(self, *args):
        self._hp_bg.pos = self.health_holder.pos
        self._hp_bg.size = self.health_holder.size
        self._update_hp_bar()

    def _update_hp_bar(self):
        frac = max(0.0, self.health / 100.0)
        self._hp_bar.pos = self.health_holder.pos
        self._hp_bar.size = (self.health_holder.width * frac, self.health_holder.height)
        self._hp_color.rgba = [1 - frac, 0.3 + 0.5 * frac, 0.2, 1]


# Each row of the guide: a real game icon next to a short, plain explanation.
GUIDE_ROWS = [
    ("player", "Tap anywhere on the screen and your character walks there."),
    ("coin", "Collect every coin to finish a level, before the timer at the top runs out."),
    ("monster", "Monsters drain your health on contact. The dots above a monster show how many "
                "hits it takes to defeat. From world 4 they chase you and turn bright red. "
                "Outrun them or shoot them."),
    ("fire", "Fire sweeps across the screen. From world 3 it grows and shrinks as it moves."),
    ("freezer", "Grab the blue freeze clock to freeze every monster for a few seconds. It is rare."),
    ("gun", "Tap the gun to shoot. It automatically hits the nearest monster, so no aiming is "
            "needed. You get a few shots; from world 4 the gun reloads on its own and an orange "
            "dial shows the wait."),
]

GUIDE_TIPS = [
    "Your health bar is at the top left. Keep it up and avoid contact.",
    "Finish a level with more health left to earn up to 3 stars.",
    "Tap the Auto button during a level to let the computer play, and tap again to take over.",
]


class GuideScreen(StyledScreen):
    # A readable reference of every part of the game, using the same icons the
    # game draws so it is easy to recognise.
    theme_world = 3

    def build(self):
        outer = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))
        outer.add_widget(Label(text="Game Guide", font_size=sp(32), bold=True,
                               size_hint_y=0.1, color=[1, 1, 1, 1]))

        scroll = ScrollView(size_hint_y=0.76)
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(0, dp(4)))
        col.bind(minimum_height=col.setter("height"))

        for kind, text in GUIDE_ROWS:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(84), spacing=dp(14))
            row.add_widget(self._make_icon(kind))
            label = Label(text=text, font_size=sp(18), color=[1, 1, 1, 1],
                          halign="left", valign="middle")
            label.bind(size=lambda lb, *a: setattr(lb, "text_size", lb.size))
            row.add_widget(label)
            col.add_widget(row)

        for tip in GUIDE_TIPS:
            t = Label(text="- " + tip, font_size=sp(18), color=[1, 1, 1, 1],
                      halign="left", valign="top", size_hint_y=None)
            t.bind(width=lambda lb, *a: setattr(lb, "text_size", (lb.width, None)))
            t.bind(texture_size=lambda lb, *a: setattr(lb, "height", lb.texture_size[1] + dp(8)))
            col.add_widget(t)

        scroll.add_widget(col)
        outer.add_widget(scroll)

        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.12)
        back.bind(on_release=lambda *a: app().go("menu"))
        outer.add_widget(back)
        self.root_layout.add_widget(outer)

    def _make_icon(self, kind):
        # Build a small, fixed-width instance of the real game sprite. Drawn once
        # (not animated) so it stays a light static icon.
        if kind == "player":
            icon = graphics.PlayerSprite(size_hint=(None, 1), width=dp(60))
        elif kind == "coin":
            icon = graphics.Coin(size_hint=(None, 1), width=dp(60))
        elif kind == "monster":
            icon = graphics.MonsterSprite(size_hint=(None, 1), width=dp(60))
            icon.mtype, icon.max_hp, icon.hp = 1, 1, 1
        elif kind == "fire":
            icon = graphics.Hazard(size_hint=(None, 1), width=dp(60))
        elif kind == "freezer":
            icon = graphics.Freezer(size_hint=(None, 1), width=dp(60))
        else:  # gun
            icon = GunButton(size_hint=(None, 1), width=dp(76))
            icon.ammo, icon.ready = 2, True
        return icon


class AutoPlayerScreen(StyledScreen):
    # Lets the player tune how the built-in genetic-algorithm agent plays when the
    # Auto button is on: its play style and how often it re-decides.
    theme_world = 6

    STYLES = [("cautious", "Cautious"), ("balanced", "Balanced"), ("aggressive", "Aggressive")]
    SPEEDS = [("slow", "Slow"), ("normal", "Normal"), ("fast", "Fast")]

    def build(self):
        box = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(12),
                        size_hint=(0.88, 0.92), pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="Auto Player", font_size=sp(32), bold=True,
                             size_hint_y=0.12, color=[1, 1, 1, 1]))
        intro = Label(text="The Auto button lets a genetic-algorithm agent play for you.\n"
                           "Choose how it plays:",
                      font_size=sp(16), size_hint_y=0.14, color=[1, 1, 1, 0.9],
                      halign="center", valign="middle")
        intro.bind(size=lambda l, *a: setattr(l, "text_size", l.size))
        box.add_widget(intro)

        box.add_widget(Label(text="Play style  (safety vs collecting coins)", font_size=sp(18),
                             bold=True, size_hint_y=0.08, color=[1, 1, 1, 1]))
        self.style_btns = {}
        style_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=0.14)
        for key, label in self.STYLES:
            b = StyledButton(text=label, font_size=sp(18))
            b.bind(on_release=lambda w, k=key: self._set("ga_style", k))
            self.style_btns[key] = b
            style_row.add_widget(b)
        box.add_widget(style_row)

        box.add_widget(Label(text="Reaction speed  (how often it re-decides)", font_size=sp(18),
                             bold=True, size_hint_y=0.08, color=[1, 1, 1, 1]))
        self.speed_btns = {}
        speed_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=0.14)
        for key, label in self.SPEEDS:
            b = StyledButton(text=label, font_size=sp(18))
            b.bind(on_release=lambda w, k=key: self._set("ga_speed", k))
            self.speed_btns[key] = b
            speed_row.add_widget(b)
        box.add_widget(speed_row)

        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.12)
        back.bind(on_release=lambda *a: app().go("settings"))
        box.add_widget(back)
        self.root_layout.add_widget(box)

    def on_enter(self):
        app().audio.play_menu_music()
        self._refresh()

    def _set(self, key, value):
        app().state.set_setting(key, value)
        self._refresh()

    def _refresh(self):
        state = app().state
        style = state.get_setting("ga_style")
        speed = state.get_setting("ga_speed")
        for key, btn in self.style_btns.items():
            btn.bg = [0.2, 0.7, 0.4, 1] if key == style else [0.35, 0.4, 0.5, 1]
        for key, btn in self.speed_btns.items():
            btn.bg = [0.2, 0.7, 0.4, 1] if key == speed else [0.35, 0.4, 0.5, 1]


class MultiplayerMenuScreen(StyledScreen):
    # Pick whether to host a game or join one.
    def build(self):
        box = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(20),
                        size_hint=(0.7, 0.8), pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="Multiplayer", font_size=sp(44), bold=True,
                             color=[1, 0.85, 0.2, 1], size_hint_y=0.3))
        info = Label(text="Play with a friend over the network.\n"
                          "One device hosts and the other joins with the host's address.",
                     font_size=sp(16), color=[1, 1, 1, 0.9], halign="center",
                     valign="middle", size_hint_y=0.22)
        info.bind(size=lambda l, *a: setattr(l, "text_size", l.size))
        box.add_widget(info)
        host = StyledButton(text="Host Game", bg=[0.2, 0.7, 0.4, 1])
        join = StyledButton(text="Join Game", bg=[0.25, 0.5, 0.9, 1])
        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1])
        host.bind(on_release=lambda *a: app().go("mphost"))
        join.bind(on_release=lambda *a: app().go("mpjoin"))
        back.bind(on_release=lambda *a: app().go("menu"))
        for b in (host, join, back):
            box.add_widget(b)
        self.root_layout.add_widget(box)

    def on_enter(self):
        app().audio.play_menu_music()


class HostScreen(StyledScreen):
    # Hosts a 2-player game: shows this device's address, lets the host pick the
    # game type, waits for a player to join, then starts.
    MODES = [("coop", "Co-op"), ("versus", "Versus")]

    def build(self):
        self.net = None
        self._poll = None
        self._ready = False
        self._handed_off = False
        self._ip_token = 0
        box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10),
                        size_hint=(0.86, 0.94), pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="Host a Game", font_size=sp(30), bold=True,
                             color=[1, 1, 1, 1], size_hint_y=0.1))
        self.addr_label = Label(text="", font_size=sp(20), bold=True, color=[0.6, 0.95, 1, 1],
                                halign="center", valign="middle", size_hint_y=0.13)
        self.addr_label.bind(size=lambda l, *a: setattr(l, "text_size", l.size))
        box.add_widget(self.addr_label)
        # Help for playing across the internet (the local address only works on
        # the same Wi-Fi). Filled in once the public address is looked up.
        self.inet_label = Label(text="", font_size=sp(14), color=[1, 1, 1, 0.85],
                                halign="center", valign="middle", size_hint_y=0.16)
        self.inet_label.bind(size=lambda l, *a: setattr(l, "text_size", l.size))
        box.add_widget(self.inet_label)
        box.add_widget(Label(text="Game type", font_size=sp(18), bold=True,
                             size_hint_y=0.07, color=[1, 1, 1, 1]))
        self.mode_btns = {}
        row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=0.14)
        for key, label in self.MODES:
            b = StyledButton(text=label, font_size=sp(18))
            b.bind(on_release=lambda w, k=key: self._set_mode(k))
            self.mode_btns[key] = b
            row.add_widget(b)
        box.add_widget(row)
        self.status = Label(text="", font_size=sp(17), color=[1, 1, 1, 0.9], size_hint_y=0.12)
        box.add_widget(self.status)
        self.start_btn = StyledButton(text="Start", bg=[0.3, 0.3, 0.35, 1], size_hint_y=0.14)
        self.start_btn.bind(on_release=lambda *a: self._start())
        self.start_btn.disabled = True
        box.add_widget(self.start_btn)
        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.12)
        back.bind(on_release=lambda *a: self._leave())
        box.add_widget(back)
        self.root_layout.add_widget(box)

    def on_enter(self):
        app().audio.play_menu_music()
        self._handed_off = False
        self._begin_listening()
        # Look up the internet address once per visit, in the background so the
        # UI never blocks on the network.
        self.inet_label.text = "Checking your internet address..."
        self._ip_token += 1
        token = self._ip_token
        threading.Thread(target=self._fetch_public_ip, args=(token, net.DEFAULT_PORT),
                         daemon=True).start()
        self._poll = Clock.schedule_interval(self._check, 0.2)

    def _begin_listening(self):
        # Open (or re-open) the listening socket so a player can join. The host
        # only accepts one connection at a time, so this is called again if a
        # player connects and then leaves, to keep the host waiting.
        if self.net is not None:
            self.net.stop()
        self._ready = False
        self.start_btn.disabled = True
        self.start_btn.bg = [0.3, 0.3, 0.35, 1]
        # Hosting on Windows shows a Defender Firewall dialog the first time;
        # iOS shows a Local Network privacy prompt to the joining device. If
        # either is denied, the other player cannot reach the host.
        self.status.text = ("Waiting for a player to join.\n"
                            "If your firewall asks to allow CoinTex, click Allow.")
        self._refresh_mode()
        self.net = net.NetHost()
        try:
            self.net.start_listening()
            self.addr_label.text = "Same Wi-Fi address\n{}   port {}".format(
                net.get_local_ip(), self.net.port)
        except Exception as error:
            self.addr_label.text = "Could not start hosting."
            self.status.text = str(error)

    def _fetch_public_ip(self, token, port):
        ip = net.get_public_ip()
        Clock.schedule_once(lambda dt: self._show_public_ip(token, port, ip), 0)

    def _show_public_ip(self, token, port, ip):
        # Ignore a result that arrives after the screen was left or re-entered.
        if token != self._ip_token:
            return
        if ip:
            self.inet_label.text = (
                "Internet play: forward TCP port {} on your router,\n"
                "then give the other player this address:\n"
                "{}   port {}".format(port, ip, port))
        else:
            self.inet_label.text = (
                "Internet play: forward TCP port {} on your router\n"
                "and share your public IP address.".format(port))

    def on_leave(self):
        # Bumping the token makes any in-flight public-IP lookup discard itself.
        self._ip_token += 1
        if self._poll is not None:
            self._poll.cancel()
            self._poll = None
        if self.net is not None and not self._handed_off:
            self.net.stop()
        if not self._handed_off:
            self.net = None

    def _set_mode(self, key):
        app().state.set_setting("mp_mode", key)
        self._refresh_mode()

    def _refresh_mode(self):
        current = app().state.get_setting("mp_mode")
        for key, btn in self.mode_btns.items():
            btn.bg = [0.2, 0.7, 0.4, 1] if key == current else [0.35, 0.4, 0.5, 1]

    def _check(self, dt):
        if self.net is None:
            return
        while True:
            try:
                msg = self.net.inbox.get_nowait()
            except Exception:
                break
            kind = msg.get("t")
            if kind == "_connected":
                self.status.text = "A player is connecting..."
            elif kind == "hello":
                if msg.get("version") != net.PROTOCOL_VERSION:
                    self._begin_listening()
                    self.status.text = "A player with a different game version tried to join."
                    return
                self._ready = True
                self.status.text = "A player joined. Tap Start."
                self.start_btn.disabled = False
                self.start_btn.bg = [0.2, 0.7, 0.4, 1]
            elif kind in ("leave", "_disconnected"):
                # The host stopped listening once that player connected, so open
                # the listener again to accept a fresh join.
                self._begin_listening()
                return

    def _start(self):
        if not self._ready or self.net is None:
            return
        mode = app().state.get_setting("mp_mode")
        seed = random.randint(1, 2000000000)
        self.net.send_start(mode, levels.MP_LEVEL, seed)
        self._handed_off = True
        app().start_mp_host(mode, seed, self.net)

    def _leave(self):
        if self.net is not None and not self._handed_off:
            self.net.stop()
            self.net = None
        app().go("multiplayer")


class JoinScreen(StyledScreen):
    # Joins a hosted game by typing the host's address.
    def build(self):
        self.net = None
        self._poll = None
        self._handed_off = False
        box = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14),
                        size_hint=(0.82, 0.82), pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="Join a Game", font_size=sp(34), bold=True,
                             color=[1, 1, 1, 1], size_hint_y=0.16))
        prompt = Label(text="Type the host's address (shown on the host's screen).\n"
                            "It can be a same-Wi-Fi address or a public internet one.",
                       font_size=sp(16), color=[1, 1, 1, 0.9], halign="center",
                       valign="middle", size_hint_y=0.16)
        prompt.bind(size=lambda l, *a: setattr(l, "text_size", l.size))
        box.add_widget(prompt)
        self.ip_input = TextInput(text="", multiline=False, font_size=sp(22),
                                  size_hint_y=0.16, write_tab=False)
        box.add_widget(self.ip_input)
        self.status = Label(text="", font_size=sp(17), color=[1, 1, 1, 0.9], size_hint_y=0.12)
        box.add_widget(self.status)
        self.connect_btn = StyledButton(text="Connect", bg=[0.2, 0.7, 0.4, 1], size_hint_y=0.16)
        self.connect_btn.bind(on_release=lambda *a: self._connect())
        box.add_widget(self.connect_btn)
        back = StyledButton(text="Back", bg=[0.45, 0.45, 0.5, 1], size_hint_y=0.14)
        back.bind(on_release=lambda *a: self._leave())
        box.add_widget(back)
        self.root_layout.add_widget(box)

    def on_enter(self):
        app().audio.play_menu_music()
        self._handed_off = False
        self.status.text = ""
        self.connect_btn.disabled = False
        # Use the last address that worked, or fall back to this device's own
        # subnet (e.g. "192.168.1.") so the joiner only types the host's last
        # number when they are on the same Wi-Fi.
        last = app().state.get_setting("mp_last_ip")
        self.ip_input.text = last if last else net.local_subnet_prefix()
        self.ip_input.cursor = (len(self.ip_input.text), 0)

    def on_leave(self):
        if self._poll is not None:
            self._poll.cancel()
            self._poll = None
        if self.net is not None and not self._handed_off:
            self.net.stop()
        if not self._handed_off:
            self.net = None

    def _connect(self):
        ip = self.ip_input.text.strip()
        if not ip:
            self.status.text = "Please type the host's address."
            return
        self.status.text = "Connecting..."
        self.connect_btn.disabled = True
        self.net = net.NetClient()
        self.net.connect(ip, net.DEFAULT_PORT)
        if self._poll is None:
            self._poll = Clock.schedule_interval(self._check, 0.1)

    def _check(self, dt):
        if self.net is None:
            return
        while True:
            try:
                msg = self.net.inbox.get_nowait()
            except Exception:
                break
            kind = msg.get("t")
            if kind == "_connect_failed":
                self.status.text = "Could not connect. Check the address and Wi-Fi."
                self.connect_btn.disabled = False
                self.net.stop()
                self.net = None
                return
            elif kind == "_connected":
                self.status.text = "Connected. Waiting for the host to start..."
            elif kind == "start":
                if msg.get("version") != net.PROTOCOL_VERSION:
                    self.status.text = "The host has a different game version."
                    self.connect_btn.disabled = False
                    self.net.stop()
                    self.net = None
                    return
                app().state.set_setting("mp_last_ip", self.ip_input.text.strip())
                self._handed_off = True
                app().start_mp_client(msg.get("mode", "coop"), msg.get("seed", 0), self.net)
                return
            elif kind in ("leave", "_disconnected"):
                self.status.text = "The host closed the game."
                self.connect_btn.disabled = False
                self.net.stop()
                self.net = None
                return

    def _leave(self):
        if self.net is not None and not self._handed_off:
            self.net.stop()
            self.net = None
        app().go("multiplayer")
