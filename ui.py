# Menu, navigation and settings screens, plus a few reusable widgets.
# Everything is drawn with the canvas / standard widgets, no image files.
# The actual gameplay screen lives in main.py.

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.slider import Slider
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import sp, dp
from kivy.properties import ListProperty

import graphics
import levels

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
    "Created by Ahmed Fawzy Gad.\n"
    "Email: ahmed.f.gad@gmail.com"
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
        settings = StyledButton(text="Settings", bg=[0.25, 0.5, 0.9, 1])
        play.bind(on_release=lambda *a: app().go("worldmap"))
        settings.bind(on_release=lambda *a: app().go("settings"))
        box.add_widget(play)
        box.add_widget(settings)
        self.stars = Label(text="", font_size=sp(18), color=[1, 1, 1, 0.85], size_hint_y=0.2)
        box.add_widget(self.stars)
        self.root_layout.add_widget(box)

    def on_enter(self):
        running = app()
        running.audio.play_menu_music()
        self.stars.text = "Stars collected: {}".format(running.state.total_stars())


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
            # Show the world and level number on every button, locked or not.
            label = "W{} L{}".format(lvl["world"], lvl["world_index"])
            if unlocked:
                text = label + ("\n" + "*" * stars if stars else "")
                btn = StyledButton(text=text, bg=[0.25, 0.55, 0.9, 1], halign="center")
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

        about = StyledButton(text="About", bg=[0.25, 0.5, 0.9, 1], size_hint_y=0.12)
        about.bind(on_release=lambda *a: app().go("about"))
        box.add_widget(about)

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
        back.bind(on_release=lambda *a: app().go("settings"))
        outer.add_widget(back)
        self.root_layout.add_widget(outer)

    def on_enter(self):
        app().audio.play_menu_music()
