# CoinTex main file.
#
# The game is a top-down coin collector. You move your character around a level
# to pick up all the coins while dodging monsters and fire, and you can shoot
# the nearest monster. Levels, graphics, audio, saving and the menu screens live
# in separate modules (levels.py, graphics.py, audio.py, state.py, ui.py). This
# file holds the app, the gameplay screen and the rules.

import os
import sys
import math
import random

import kivy.app
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import sp, dp

import queue

import levels
import graphics
import ui
import autoplay
import net
from state import GameState
from audio import AudioManager

# Tuning values. Positions are kept as a center point in 0..1 over the play area.
PLAYER_SPEED = 0.6          # how fast the player moves, screens per second
# A monster's speed is capped below the player's so a chasing monster can always
# be outrun. This keeps chase levels fair for a human and reactable for the GA.
MAX_MONSTER_SPEED = 0.45
PROJECTILE_SPEED = 1.2
FIRE_COOLDOWN = 0.6         # seconds between shots
CONTACT_DAMAGE = 60.0       # default; per-level value comes from the level data
COIN_POINTS = 100
KILL_POINTS = 150
TIME_BONUS = 4              # score per second left when a level has a time limit
RESPAWN_DELAY = 3.0         # seconds before a killed monster comes back
FREEZE_DURATION = 5.0       # seconds the monsters stay frozen after a pickup

PLAYER_SIZE = (0.10, 0.14)
MONSTER_SIZE = (0.11, 0.14)
COIN_SIZE = (0.045, 0.06)
HAZARD_SIZE = (0.05, 0.08)
PROJECTILE_SIZE = (0.035, 0.05)
FREEZER_SIZE = (0.05, 0.07)
RESPAWN_MARKER_SIZE = (0.07, 0.10)
RELOAD_SECONDS = 5.0        # time for the gun to refill after it runs out (world 4+)
DOWN_DELAY = 3.0            # seconds a downed player waits before coming back (2-player)
# Player 1 is blue, player 2 is orange, so the two are easy to tell apart.
PLAYER_COLORS = ([0.20, 0.62, 1.0], [1.0, 0.55, 0.2])

# A short heads-up shown once before the first level of a world that brings a new
# mechanic, so the player is ready for it. Keyed by world number.
WORLD_INTROS = {
    2: ("Faster Enemies",
        "From here on, monsters and fire move quicker.\nKeep moving and stay sharp!"),
    3: ("Pulsing Fire",
        "Fires now grow and shrink as they move.\nTheir danger zone gets bigger and smaller,\nso time your crossings."),
    4: ("Chasers and a Reloading Gun",
        "Monsters now chase you when you get close\n(watch for the red glowing one).\nGood news: your gun now reloads on its own\nafter you run out, so shoot a chaser to clear it."),
    5: ("Less Forgiving",
        "Hits hurt more from now on.\nAvoid contact and keep your health up."),
    6: ("Final World",
        "Everything at once: fast chasers, pulsing fire,\nand hard hits. Good luck!"),
}

# Shown once, on the first level the player enters, so they know how the gun works.
GUN_INTRO = ("Your Gun",
             "Tap the gun button (bottom right) to shoot.\n"
             "It automatically hits the NEAREST monster,\nso you never need to aim.\n"
             "You have a few shots in each level.")

# Shown once, before the first level that contains a freeze clock.
FREEZER_INTRO = ("Freeze Clock",
                 "Sometimes a blue freeze clock appears in a level.\n"
                 "Grab it to freeze every monster for a few seconds,\n"
                 "a safe moment to collect coins or slip past.\nIt is rare, so use it well.")

# Shown once, before the first level where a monster takes more than one hit.
HP_INTRO = ("Tougher Monsters",
            "Monsters now take more than one hit to defeat.\n"
            "The dots above a monster show how many hits it needs.\n"
            "Keep firing at it, or just dodge it.")


def place(sprite):
    # Set a sprite's pos_hint from its center (cx, cy) and its size_hint.
    shw, shh = sprite.size_hint
    sprite.pos_hint = {"x": sprite.cx - shw / 2, "y": sprite.cy - shh / 2}


class ResultOverlay(ModalView):
    """Shown when a level is won or lost.

    Optional ``stats`` dict — when present, renders a structured stats
    grid (Coins / Score / Time / Health) below the title in two-column
    label-value form, ported from GateRunner's LevelResultDialog.
    Callers that only pass ``lines`` keep the old behaviour.
    """

    def __init__(self, title, lines, buttons, stars=None, stats=None, **kwargs):
        # Taller than before to fit the stats grid.
        super().__init__(size_hint=(0.84, 0.74), auto_dismiss=False, **kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(10))
        with box.canvas.before:
            Color(0.10, 0.12, 0.18, 0.98)
            self._bg = RoundedRectangle(radius=[dp(16)])
        box.bind(pos=lambda *a: setattr(self._bg, "pos", box.pos),
                 size=lambda *a: setattr(self._bg, "size", box.size))
        box.add_widget(Label(text=title, font_size=sp(30), bold=True,
                             color=[1, 0.85, 0.2, 1], size_hint_y=0.18))
        if stars is not None:
            box.add_widget(graphics.StarRow(earned=stars, total=3, size_hint_y=0.20))
        if stats:
            # Two-column grid: small uppercase label on the left, bold
            # value on the right. Drives at-a-glance readability — the
            # player can tell what they did this run beyond the score.
            grid = GridLayout(cols=2, spacing=(dp(8), dp(4)),
                              size_hint_y=0.36,
                              padding=(dp(16), 0, dp(16), 0))
            for key, value, accent in stats:
                lbl = Label(text=key, font_size=sp(15), color=(1, 1, 1, 0.78),
                            halign="right", valign="middle", size_hint_x=0.45)
                lbl.bind(size=lambda l, *_: setattr(l, "text_size", l.size))
                grid.add_widget(lbl)
                val = Label(text=value, font_size=sp(16), bold=True,
                            color=accent, markup=True,
                            halign="left", valign="middle", size_hint_x=0.55)
                val.bind(size=lambda l, *_: setattr(l, "text_size", l.size))
                grid.add_widget(val)
            box.add_widget(grid)
        else:
            box.add_widget(Label(text="\n".join(lines), font_size=sp(20),
                                 color=[1, 1, 1, 1], halign="center",
                                 size_hint_y=0.22))
        row = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=0.22)
        for text, color, callback in buttons:
            btn = ui.StyledButton(text=text, bg=color)
            btn.bind(on_release=lambda b, cb=callback: (self.dismiss(), cb()))
            row.add_widget(btn)
        box.add_widget(row)
        self.add_widget(box)


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # The world holds the background and all sprites. The hud sits on top.
        self.world = FloatLayout()
        self.bg = graphics.Background(levels.get_world(1), size_hint=(1, 1))
        self.world.add_widget(self.bg)
        self.add_widget(self.world)
        self.hud = FloatLayout()
        self.add_widget(self.hud)
        self._build_hud()

        self.level = None
        self.active = False
        self.paused = False
        self.player = None
        self.monsters = []
        self.coins = []
        self.hazards = []
        self.projectiles = []
        self.freezers = []
        self.pending_respawns = []   # seconds left before each killed monster returns
        self.freeze_time = 0.0
        self._damage_sfx_cd = 0.0
        self._update_event = None
        # Auto play: the built-in genetic algorithm can take over from the player.
        self.auto_mode = False
        self.auto = autoplay.AutoPlayer(self)

        # Two-player state. In a single-player game these stay at their defaults
        # and none of the multiplayer code below runs.
        self.multiplayer = False
        self.role = None             # "host", "client", or None for single player
        self.mode = None             # "coop" or "versus"
        self.net = None              # a net.NetHost or net.NetClient while connected
        self.player2 = None          # the second character, only in multiplayer
        self.local_player = None     # the character this device controls
        self.remote_player = None    # the other device's character
        self._net_event = None       # the host's snapshot broadcast timer
        self._rng = random           # swapped for a seeded one in multiplayer
        self._last_input = (0.1, 0.12)   # last target a client sent to the host
        self._ended = False          # guards the one-time multiplayer end overlay

    def _build_hud(self):
        self.coin_label = Label(text="", font_size=sp(20), bold=True, color=[1, 1, 1, 1],
                                size_hint=(0.25, 0.06), pos_hint={"x": 0.02, "top": 0.99})
        self.level_label = Label(text="", font_size=sp(20), bold=True, color=[1, 1, 1, 1],
                                 size_hint=(0.2, 0.06), pos_hint={"center_x": 0.5, "top": 0.99})
        self.time_label = Label(text="", font_size=sp(20), bold=True, color=[1, 1, 0.5, 1],
                                size_hint=(0.2, 0.06), pos_hint={"right": 0.78, "top": 0.99})
        self.hud.add_widget(self.coin_label)
        self.hud.add_widget(self.level_label)
        self.hud.add_widget(self.time_label)

        # health bar (drawn in code), top-left under the coin label
        self.health_holder = FloatLayout(size_hint=(0.25, 0.03), pos_hint={"x": 0.02, "top": 0.92})
        with self.health_holder.canvas.before:
            Color(0, 0, 0, 0.4)
            self._hp_bg = Rectangle()
            self._hp_color = Color(0.2, 0.8, 0.3, 1)
            self._hp_bar = Rectangle()
        self.health_holder.bind(pos=self._sync_health, size=self._sync_health)
        self.hud.add_widget(self.health_holder)

        # Extra line shown only in a 2-player game: both players' health, and in
        # versus the two coin counts. It stays empty (invisible) in single player.
        self.mp_label = Label(text="", font_size=sp(16), bold=True, color=[1, 1, 1, 1],
                              halign="left", size_hint=(0.4, 0.05),
                              pos_hint={"x": 0.02, "top": 0.88})
        self.mp_label.bind(size=lambda *a: setattr(self.mp_label, "text_size", self.mp_label.size))
        self.hud.add_widget(self.mp_label)

        self.pause_btn = ui.StyledButton(text="II", bg=[0.3, 0.3, 0.4, 0.9],
                                         size_hint=(0.08, 0.08), pos_hint={"right": 0.99, "top": 0.99})
        self.pause_btn.bind(on_release=lambda *a: self._open_pause())
        self.hud.add_widget(self.pause_btn)

        self.fire_btn = ui.GunButton(size_hint=(0.17, 0.13), pos_hint={"right": 0.98, "y": 0.03})
        self.fire_btn.bind(on_release=lambda *a: self.fire())
        self.hud.add_widget(self.fire_btn)

        # circular freeze countdown, shown only while a freeze is active
        self.freeze_timer = graphics.FreezeTimer(size_hint=(0.09, 0.14),
                                                 pos_hint={"center_x": 0.5, "top": 0.90})
        self.freeze_timer.opacity = 0
        self.hud.add_widget(self.freeze_timer)

        # Auto play toggle (bottom-left). Tapping it lets the built-in genetic
        # algorithm take over, and tapping again returns to manual control.
        self.auto_btn = ui.StyledButton(text="Auto: Off", bg=[0.45, 0.45, 0.5, 1],
                                        font_size=sp(16), size_hint=(0.17, 0.08),
                                        pos_hint={"x": 0.02, "y": 0.05})
        self.auto_btn.bind(on_release=lambda *a: self._toggle_auto())
        self.hud.add_widget(self.auto_btn)

        # Shows while the agent is in control so it is clear who is playing.
        self.auto_indicator = Label(text="AUTO", font_size=sp(16), bold=True,
                                    color=[0.3, 1.0, 0.5, 1], opacity=0,
                                    size_hint=(0.17, 0.05), pos_hint={"x": 0.02, "y": 0.14})
        self.hud.add_widget(self.auto_indicator)

    def _sync_health(self, *args):
        self._hp_bg.pos = self.health_holder.pos
        self._hp_bg.size = self.health_holder.size
        self._update_health_bar()

    def _update_health_bar(self):
        # The bar shows the health of the character this device controls.
        who = self.local_player
        frac = 0 if (self.level is None or who is None) else max(0.0, who.health / who.max_health)
        self._hp_bar.pos = self.health_holder.pos
        self._hp_bar.size = (self.health_holder.width * frac, self.health_holder.height)
        # green when healthy, red when low
        self._hp_color.rgba = [1 - frac, 0.3 + 0.5 * frac, 0.2, 1]

    def _players(self):
        # The characters in play: one normally, two in a multiplayer game.
        if self.player2 is not None:
            return [self.player, self.player2]
        return [self.player] if self.player is not None else []

    # ----- building a level -----
    def load_level(self, index, multiplayer=False, role=None, mode=None, seed=None):
        self._clear_sprites()
        self.multiplayer = multiplayer
        self.role = role
        self.mode = mode
        self._ended = False
        # A seeded random source makes the host and the client lay out the arena
        # exactly the same way. Single player keeps using the module's random.
        self._rng = random.Random(seed) if (multiplayer and seed is not None) else random

        if index == levels.MP_LEVEL:
            self.level = levels.get_mp_level(seed)
        else:
            self.level = levels.get_level(index)
        self.index = index
        theme = levels.get_world(self.level["world"])
        self.bg.set_theme(theme)
        # In-level music changes per world.
        kivy.app.App.get_running_app().audio.play_level_music(self.level["world"])

        self.score = 0
        self.kills = 0
        self._damage_sfx_cd = 0.0
        self.time_left = self.level["time_limit"]
        self.freeze_time = 0.0
        self.pending_respawns = []
        self.monster_speed = 0.45 / self.level["monster_speed"]
        # Behavior knobs read once per level (see levels.py). These scale the
        # difficulty without adding any sprites.
        self.enemy_speed_mult = self.level["enemy_speed_mult"]
        self.chase_range = self.level["chase_range"]
        self.chase_time = self.level["chase_time"]
        self.pulse_amp = self.level["pulse_amp"]
        self.pulse_period = self.level["pulse_period"]
        self.contact_damage = self.level["contact_damage"]
        self.reload_gun = self.level["gun_reload"]
        self.active = True
        self.paused = False

        # Player 1 starts bottom-left. Per-player state (health, ammo, coins)
        # lives on the sprite so the same code handles one or two players.
        self.player = self._make_player(0.1, 0.12, PLAYER_COLORS[0])
        if multiplayer:
            self.player2 = self._make_player(0.9, 0.12, PLAYER_COLORS[1])
        else:
            self.player2 = None
        # Decide which character this device drives. The host drives player 1,
        # the client drives player 2, single player drives player 1.
        if role == "client":
            self.local_player, self.remote_player = self.player2, self.player
        else:
            self.local_player, self.remote_player = self.player, self.player2

        # monsters (they respawn when killed, so they cannot all be cleared)
        for i in range(self.level["monsters"]):
            self._spawn_monster()

        # coins, spread across the width in sections like the original game. Each
        # coin keeps an index so a host can tell a client which coins remain
        # without sending their positions (both built the same layout).
        section = 1.0 / self.level["coins"]
        for k in range(self.level["coins"]):
            coin = graphics.Coin(size_hint=COIN_SIZE)
            coin.index = k
            coin.cx = self._rng.uniform(section * k + 0.03, section * (k + 1) - 0.03)
            coin.cx = min(max(coin.cx, 0.05), 0.95)
            coin.cy = self._rng.uniform(0.2, 0.9)
            place(coin)
            self.world.add_widget(coin)
            coin.start()
            self.coins.append(coin)

        # Fires sweep all the way across the screen along a random line, either
        # left to right or top to bottom. The line position is random but the
        # sweep is full width or full height, so a fire never sits still on a coin
        # and instead passes over it. That keeps the screen fair to cross and
        # means no coin is ever blocked for good.
        for i in range(self.level["fires"]):
            hazard = graphics.Hazard(size_hint=HAZARD_SIZE)
            if self._rng.random() < 0.5:
                # horizontal sweep across x at a fixed random height
                y = self._rng.uniform(0.18, 0.85)
                hazard.ax, hazard.ay = 0.08, y
                hazard.bx, hazard.by = 0.92, y
            else:
                # vertical sweep up and down at a fixed random column
                x = self._rng.uniform(0.08, 0.92)
                hazard.ax, hazard.ay = x, 0.12
                hazard.bx, hazard.by = x, 0.9
            hazard.t = self._rng.uniform(0, 1)
            hazard.period = self.level["fire_speed"]
            hazard.pt = self._rng.uniform(0, 1)   # pulse phase, separate from sweep
            hazard.size_factor = 1.0
            hazard.cx, hazard.cy = hazard.ax, hazard.ay
            place(hazard)
            self.world.add_widget(hazard)
            hazard.start()
            self.hazards.append(hazard)

        # rare freeze pickups
        for i in range(self.level["freezers"]):
            freezer = graphics.Freezer(size_hint=FREEZER_SIZE)
            freezer.cx = self._rng.uniform(0.15, 0.9)
            freezer.cy = self._rng.uniform(0.2, 0.85)
            place(freezer)
            self.world.add_widget(freezer)
            freezer.start()
            self.freezers.append(freezer)

        self.fire_btn.ammo = self.local_player.ammo
        self.fire_btn.ready = True
        self.freeze_timer.opacity = 0
        self._refresh_hud()

        # The Auto player is for single player only; hide it in a 2-player game.
        if self.multiplayer:
            self.auto_mode = False
            self.auto.stop()
            self.auto_btn.opacity = 0
            self.auto_btn.disabled = True
            self.auto_indicator.opacity = 0
        else:
            self.auto_btn.opacity = 1
            self.auto_btn.disabled = False
            # Keep the chosen play mode (manual or auto) when moving between levels.
            self._refresh_auto_button()
            if self.auto_mode:
                self.auto.start()
            else:
                self.auto.stop()

    def _make_player(self, cx, cy, color):
        # Create a player character and put its per-player state on the sprite,
        # so one or two players run through the same game code.
        p = graphics.PlayerSprite(size_hint=PLAYER_SIZE)
        p.body_color = list(color)
        p.cx, p.cy = cx, cy
        p.tx, p.ty = cx, cy
        p.start_x, p.start_y = cx, cy
        p.max_health = self.level["player_health"]
        p.health = p.max_health
        p.ammo = self.level["ammo"]
        p.cooldown = 0.0
        p.reload_time = 0.0      # >0 while this player's gun is refilling
        p.collected = 0
        p.down_time = 0.0        # >0 while this player is waiting to come back
        place(p)
        self.world.add_widget(p)
        p.start()
        return p

    def _random_point(self):
        return self._rng.uniform(0.1, 0.95), self._rng.uniform(0.15, 0.95)

    def _spawn_point_away(self):
        # A random point that is not right on top of the player.
        for _ in range(10):
            x, y = self._random_point()
            if self.player is None or abs(x - self.player.cx) + abs(y - self.player.cy) > 0.35:
                return x, y
        return self._random_point()

    def _spawn_monster(self, at=None):
        monster = graphics.MonsterSprite(size_hint=MONSTER_SIZE)
        monster.mtype = max(1, min(3, self.level["monster_hp"]))
        monster.max_hp = self.level["monster_hp"]
        monster.hp = monster.max_hp
        monster.cx, monster.cy = at if at is not None else self._spawn_point_away()
        monster.tx, monster.ty = self._random_point()
        monster.speed = self.monster_speed
        monster.frozen = self.freeze_time > 0
        monster.chase_timer = 0.0   # >0 while locked onto the player
        monster.chasing = False
        place(monster)
        self.world.add_widget(monster)
        monster.start()
        self.monsters.append(monster)

    def _clear_sprites(self):
        for sprite in ([self.player, self.player2] + self.monsters + self.coins
                       + self.hazards + self.projectiles + self.freezers):
            if sprite is not None:
                sprite.stop()
                if sprite.parent:
                    sprite.parent.remove_widget(sprite)
        for entry in self.pending_respawns:
            marker = entry["marker"]
            if marker.parent:
                marker.parent.remove_widget(marker)
        self.player = None
        self.player2 = None
        self.local_player = None
        self.remote_player = None
        self.monsters = []
        self.coins = []
        self.hazards = []
        self.projectiles = []
        self.freezers = []
        self.pending_respawns = []
        self.freeze_time = 0.0

    # ----- screen lifecycle -----
    def on_enter(self):
        # Level music is started in load_level (one place only) to avoid playing
        # the same looping track twice. Here we just start the loop and keys.
        if self._update_event is None:
            self._update_event = Clock.schedule_interval(self.update, 1 / 60.0)
        # The host sends the game state to the client a few times a second. This
        # is separate from the 60fps loop because the client does not need every
        # frame to stay in step.
        if self.role == "host" and self._net_event is None:
            self._net_event = Clock.schedule_interval(self._broadcast_state, 1 / 20.0)
        Window.bind(on_key_down=self._on_key)

    def on_leave(self):
        self.auto.stop()
        if self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        if self._net_event is not None:
            self._net_event.cancel()
            self._net_event = None
        Window.unbind(on_key_down=self._on_key)
        kivy.app.App.get_running_app().audio.stop_music()
        if self.net is not None:
            self.net.stop()
            self.net = None
        self.multiplayer = False
        self.role = None
        self.mode = None
        self._clear_sprites()

    def _on_key(self, window, key, scancode, codepoint, modifiers):
        if key == 32:  # spacebar fires
            self.fire()
            return True
        return False

    # ----- input -----
    def on_touch_down(self, touch):
        # Let the HUD buttons handle their taps first.
        if super().on_touch_down(touch):
            return True
        if not self.active or self.paused or self.local_player is None:
            return False
        tx = min(max(touch.sx, 0.05), 0.95)
        ty = min(max(touch.sy, 0.05), 0.95)
        if self.role == "client":
            # The client never moves its own sprite; it asks the host to, and the
            # host's next snapshot moves it on screen.
            self._last_input = (tx, ty)
            if self.net is not None:
                self.net.send_input(tx, ty)
            return True
        self.local_player.tx, self.local_player.ty = tx, ty
        return True

    # ----- main loop -----
    def update(self, dt):
        # The client does not run the game. It only reads the host's updates and
        # draws them; everything below is for the host or for single player.
        if self.role == "client":
            self._pump_net(dt)
            return
        if not self.active or self.paused or self.player is None:
            return
        if self.role == "host":
            self._pump_net(dt)   # read the joining player's taps and shots

        # Gun cooldown and reload, tracked per player.
        for p in self._players():
            if p.cooldown > 0:
                p.cooldown -= dt
            if p.reload_time > 0:
                p.reload_time -= dt
                if p.reload_time <= 0:
                    p.reload_time = 0.0
                    p.ammo = self.level["ammo"]
                    if p is self.local_player:
                        kivy.app.App.get_running_app().audio.play_sfx("reload")

        frozen = self.freeze_time > 0
        if frozen:
            self.freeze_time -= dt
            if self.freeze_time <= 0:
                self.freeze_time = 0.0
                for monster in self.monsters:
                    monster.frozen = False
                frozen = False

        # Move each living player toward its target. A downed player (only in a
        # 2-player game) waits out a short timer and then comes back.
        for p in self._players():
            if p.down_time > 0:
                p.down_time -= dt
                if p.down_time <= 0:
                    self._revive_player(p)
                continue
            self._move_toward(p, p.tx, p.ty, PLAYER_SPEED * dt)

        if not frozen:
            living = [p for p in self._players() if not p.dead and p.down_time <= 0]
            # Only the monster nearest to a player may lock on, so no one is
            # pincered by two at once. With one player this is the original rule.
            nearest = None
            if self.monsters and living:
                nearest = min(self.monsters, key=lambda m:
                              min((m.cx - p.cx) ** 2 + (m.cy - p.cy) ** 2 for p in living))
            for monster in self.monsters:
                anchor = None
                if living:
                    anchor = min(living, key=lambda p:
                                 (monster.cx - p.cx) ** 2 + (monster.cy - p.cy) ** 2)
                if monster is nearest and self.chase_range > 0 and anchor is not None:
                    # Lock on when a player comes within range; the lock lasts
                    # chase_time seconds so it keeps coming briefly after you flee.
                    d = ((monster.cx - anchor.cx) ** 2
                         + (monster.cy - anchor.cy) ** 2) ** 0.5
                    if d <= self.chase_range:
                        monster.chase_timer = self.chase_time
                else:
                    monster.chase_timer = 0.0
                if monster.chase_timer > 0 and anchor is not None:
                    monster.chase_timer -= dt
                    monster.chasing = True
                    monster.tx, monster.ty = anchor.cx, anchor.cy
                else:
                    monster.chasing = False
                # Effective speed is capped below the player's so it stays escapable.
                step = min(monster.speed * self.enemy_speed_mult, MAX_MONSTER_SPEED) * dt
                reached = self._move_toward(monster, monster.tx, monster.ty, step)
                if reached and not monster.chasing:
                    monster.tx, monster.ty = self._random_point()

        for hazard in self.hazards:
            hazard.t = (hazard.t + dt * self.enemy_speed_mult / hazard.period) % 1.0
            phase = 0.5 - 0.5 * math.cos(hazard.t * 2 * math.pi)
            hazard.cx = hazard.ax + (hazard.bx - hazard.ax) * phase
            hazard.cy = hazard.ay + (hazard.by - hazard.ay) * phase
            # Pulse the fire's size (and so its hitbox) so the danger zone breathes.
            if self.pulse_amp > 0:
                hazard.pt = (hazard.pt + dt / self.pulse_period) % 1.0
                hazard.size_factor = 1.0 + self.pulse_amp * math.sin(hazard.pt * 2 * math.pi)
            place(hazard)

        self._update_projectiles(dt)
        self._process_respawns(dt)
        self._check_coins()
        self._check_freezers()
        self._check_damage(dt)
        self._update_timer(dt)
        self._update_health_bar()
        self._update_combat_hud()
        if self.multiplayer:
            self._update_mp_hud()

    def _process_respawns(self, dt):
        if not self.pending_respawns:
            return
        remaining = []
        for entry in self.pending_respawns:
            entry["t"] -= dt
            if entry["t"] <= 0:
                if entry["marker"].parent:
                    entry["marker"].parent.remove_widget(entry["marker"])
                if self.active:
                    self._spawn_monster(at=(entry["x"], entry["y"]))
            else:
                entry["marker"].seconds = entry["t"]
                entry["marker"].fraction = entry["t"] / RESPAWN_DELAY
                remaining.append(entry)
        self.pending_respawns = remaining

    def _check_freezers(self):
        for freezer in list(self.freezers):
            picker = self._toucher(freezer, factor=0.8)
            if picker is None:
                continue
            self.freezers.remove(freezer)
            freezer.stop()
            if freezer.parent:
                freezer.parent.remove_widget(freezer)
            self.freeze_time = FREEZE_DURATION
            for monster in self.monsters:
                monster.frozen = True
            self._sfx("coin")

    def _toucher(self, item, factor):
        # The first living player overlapping item, or None.
        for p in self._players():
            if p.dead or p.down_time > 0:
                continue
            if self._overlap(p, item, factor=factor):
                return p
        return None

    def _sfx(self, name):
        # Play a sound here, and on the host also tell the client to play it so
        # the joining player hears the same feedback.
        kivy.app.App.get_running_app().audio.play_sfx(name)
        if self.role == "host" and self.net is not None:
            self.net.send_event("sfx", name)

    def _update_combat_hud(self):
        # The gun button shows the state of the local player's gun.
        who = self.local_player
        self.fire_btn.ammo = who.ammo
        self.fire_btn.ready = who.cooldown <= 0
        if self.freeze_time > 0:
            self.freeze_timer.opacity = 1
            self.freeze_timer.seconds = self.freeze_time
            self.freeze_timer.fraction = self.freeze_time / FREEZE_DURATION
        else:
            self.freeze_timer.opacity = 0
        if who.reload_time > 0:
            self.fire_btn.reloading = True
            self.fire_btn.reload_seconds = who.reload_time
            self.fire_btn.reload_fraction = who.reload_time / RELOAD_SECONDS
        else:
            self.fire_btn.reloading = False

    def _update_mp_hud(self):
        # Extra two-player readout: both healths, and the coin counts in versus.
        p1, p2 = self.player, self.player2
        if p1 is None or p2 is None:
            return
        h1 = max(0, int(round(100 * p1.health / p1.max_health)))
        h2 = max(0, int(round(100 * p2.health / p2.max_health)))
        if self.mode == "versus":
            self.mp_label.text = "P1 {}%  coins {}    P2 {}%  coins {}".format(
                h1, p1.collected, h2, p2.collected)
        else:
            self.mp_label.text = "P1 {}%    P2 {}%".format(h1, h2)

    def _move_toward(self, sprite, tx, ty, step):
        dx = tx - sprite.cx
        dy = ty - sprite.cy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= step or dist == 0:
            sprite.cx, sprite.cy = tx, ty
            place(sprite)
            sprite.moving = False
            return True
        ux, uy = dx / dist, dy / dist
        # Point the sprite where it is heading so the art reflects direction.
        sprite.face_x, sprite.face_y = ux, uy
        sprite.moving = True
        sprite.cx += ux * step
        sprite.cy += uy * step
        place(sprite)
        return False

    def _px(self, sprite):
        # Pixel center of a sprite based on its normalized center.
        return (self.world.x + sprite.cx * self.world.width,
                self.world.y + sprite.cy * self.world.height)

    def _radius(self, sprite):
        base = min(sprite.size_hint[0] * self.world.width,
                   sprite.size_hint[1] * self.world.height) / 2
        # Pulsing fires grow and shrink, so the hitbox follows the visual.
        return base * getattr(sprite, "size_factor", 1.0)

    def _overlap(self, a, b, factor=0.8):
        ax, ay = self._px(a)
        bx, by = self._px(b)
        reach = (self._radius(a) + self._radius(b)) * factor
        return (ax - bx) ** 2 + (ay - by) ** 2 <= reach * reach

    # ----- combat -----
    def fire(self, shooter=None):
        # On the client, firing is a request to the host; the shot appears when
        # the host's next snapshot arrives.
        if self.role == "client":
            if self.net is not None:
                tx, ty = self._last_input
                self.net.send_input(tx, ty, fire=True)
            return
        if not self.active or self.paused or self.player is None:
            return
        if shooter is None:
            shooter = self.local_player
        if shooter is None or shooter.dead or shooter.down_time > 0:
            return
        if shooter.cooldown > 0 or shooter.ammo <= 0 or not self.monsters:
            return
        target = self._nearest_monster(to=shooter)
        if target is None:
            return
        shooter.cooldown = FIRE_COOLDOWN
        shooter.ammo -= 1
        # From world 4 on, start the reload clock once the clip is empty.
        if shooter.ammo <= 0 and self.reload_gun and shooter.reload_time <= 0:
            shooter.reload_time = RELOAD_SECONDS
        shot = graphics.Projectile(size_hint=PROJECTILE_SIZE)
        shot.cx, shot.cy = shooter.cx, shooter.cy
        shot.target = target
        place(shot)
        self.world.add_widget(shot)
        shot.start()
        self.projectiles.append(shot)
        self._sfx("shoot")

    def _nearest_monster(self, to=None):
        if to is None:
            to = self.local_player
        if to is None:
            return None
        best = None
        best_d = 999
        for monster in self.monsters:
            d = (monster.cx - to.cx) ** 2 + (monster.cy - to.cy) ** 2
            if d < best_d:
                best_d = d
                best = monster
        return best

    def _update_projectiles(self, dt):
        for shot in list(self.projectiles):
            target = shot.target if shot.target in self.monsters else self._nearest_monster(to=shot)
            if target is not None:
                shot.target = target
                self._move_toward(shot, target.cx, target.cy, PROJECTILE_SPEED * dt)
                if self._overlap(shot, target, factor=0.9):
                    self._hit_monster(target)
                    self._remove_projectile(shot)
                    continue
            else:
                shot.cy += PROJECTILE_SPEED * dt
                place(shot)
            if shot.cx < -0.1 or shot.cx > 1.1 or shot.cy < -0.1 or shot.cy > 1.1:
                self._remove_projectile(shot)

    def _remove_projectile(self, shot):
        if shot in self.projectiles:
            self.projectiles.remove(shot)
        shot.stop()
        if shot.parent:
            shot.parent.remove_widget(shot)

    def _hit_monster(self, monster):
        monster.hp -= 1
        monster.hit_flash()
        if monster.hp <= 0:
            self.kills += 1
            self.score += KILL_POINTS
            self._burst(monster, graphics.MONSTER_COLORS.get(int(monster.mtype), (1, 0.4, 0.4)))
            monster.stop()
            if monster.parent:
                monster.parent.remove_widget(monster)
            if monster in self.monsters:
                self.monsters.remove(monster)
            # It returns at the spot where it died; a countdown marker shows where.
            marker = graphics.RespawnMarker(size_hint=RESPAWN_MARKER_SIZE)
            marker.cx, marker.cy = monster.cx, monster.cy
            place(marker)
            self.world.add_widget(marker)
            self.pending_respawns.append({"t": RESPAWN_DELAY, "x": monster.cx,
                                          "y": monster.cy, "marker": marker})
            self._sfx("monster_death")
        else:
            self._sfx("hit")
        self._refresh_hud()

    def _burst(self, sprite, color):
        cx, cy = self._px(sprite)
        self.world.add_widget(graphics.ParticleBurst((cx, cy), color=color))

    # ----- coins, damage, timer -----
    def _check_coins(self):
        for coin in list(self.coins):
            picker = self._toucher(coin, factor=0.7)
            if picker is None:
                continue
            self.coins.remove(coin)
            coin.stop()
            if coin.parent:
                coin.parent.remove_widget(coin)
            picker.collected += 1
            self.score += COIN_POINTS
            self._sfx("coin")
            self._refresh_hud()
        if not self.coins and self.active:
            self._coins_cleared()

    def _coins_cleared(self):
        # The board is empty. What that means depends on the game type.
        if not self.multiplayer:
            self._win()
        elif self.mode == "versus":
            self._end_versus()
        else:
            self._end_coop(cleared=True)

    def _check_damage(self, dt):
        if self._damage_sfx_cd > 0:
            self._damage_sfx_cd -= dt
        hurt_local = False
        for p in self._players():
            if p.dead or p.down_time > 0:
                continue
            touching = False
            if self.freeze_time <= 0:  # frozen monsters do not hurt anyone
                for monster in self.monsters:
                    if self._overlap(p, monster, factor=0.7):
                        touching = True
                        break
            if not touching:
                for hazard in self.hazards:
                    if self._overlap(p, hazard, factor=0.6):
                        touching = True
                        break
            if not touching:
                continue
            p.health -= self.contact_damage * dt
            p.hit_flash()
            if p is self.local_player:
                hurt_local = True
            if p.health <= 0:
                p.health = 0
                self._player_down(p)
        # Play the hurt sound for the local player, on a short cadence.
        if hurt_local and self._damage_sfx_cd <= 0:
            self._sfx("damage")
            self._damage_sfx_cd = 0.4

    def _player_down(self, p):
        # In single player a dead player loses the level. In a 2-player game the
        # player is downed for a few seconds and then comes back, so one mistake
        # does not end the match.
        if not self.multiplayer:
            self._lose()
            return
        p.dead = True
        p.down_time = DOWN_DELAY
        self._sfx("death")
        if self.mode != "versus" and all(q.dead for q in self._players()):
            # In co-op, both players down at once ends the run.
            self._end_coop(cleared=False, reason="Both players were caught!")

    def _revive_player(self, p):
        p.down_time = 0.0
        p.dead = False
        p.health = p.max_health * 0.6
        p.cx, p.cy = p.start_x, p.start_y
        p.tx, p.ty = p.cx, p.cy
        place(p)

    def _update_timer(self, dt):
        if self.time_left is None:
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            if not self.multiplayer:
                self._lose()
            elif self.mode == "versus":
                self._end_versus()
            else:
                self._end_coop(cleared=False, reason="Out of time!")
        self._refresh_hud()

    def _refresh_hud(self):
        total = self.level["coins"]
        done = total - len(self.coins)
        if self.multiplayer and self.mode == "versus":
            self.coin_label.text = "Coins left {}".format(len(self.coins))
        else:
            self.coin_label.text = "Coins {}/{}".format(done, total)
        self.level_label.text = "Level {}".format(self.level["name"])
        if self.time_left is None:
            self.time_label.text = ""
        else:
            self.time_label.text = "Time {}".format(int(self.time_left))

    # ----- win / lose -----
    def _build_result_stats(self, score):
        """Build the stats table for ResultOverlay (label, value, accent).

        Same pattern as GateRunner's LevelResultDialog: small label on
        the left, bold numeric value on the right, accent colour per row.
        Shown both on win and loss so the player always sees what
        happened in this attempt.
        """
        total_coins = self.level["coins"] if self.level else 0
        collected = total_coins - len(self.coins)
        time_str = (
            "{}".format(int(max(0, self.time_left)))
            if self.time_left is not None else "-"
        )
        if self.time_left is not None and self.level:
            time_str += " / {}".format(int(self.level["time_limit"]))
        health = int(self.player.health) if self.player else 0
        max_h = int(self.player.max_health) if self.player else 0
        return [
            ("Score",   "[b]{}[/b]".format(score),     (1.0, 0.92, 0.40, 1.0)),
            ("Coins",   "[b]{}[/b] of {}".format(collected, total_coins),
                                                       (1.0, 0.85, 0.30, 1.0)),
            ("Time",    "[b]{}[/b]".format(time_str),  (0.65, 0.85, 1.0, 1.0)),
            ("Health",  "[b]{}[/b] / {}".format(health, max_h),
                                                       (0.95, 0.50, 0.45, 1.0)),
        ]

    def _score_and_stars(self):
        score = self.score + int(self.player.health) * 3
        if self.time_left is not None:
            score += int(self.time_left) * TIME_BONUS
        # stars: finishing = 1, plus health and (when timed) time bonuses
        stars = 1
        if self.player.health >= self.player.max_health * 0.5:
            stars += 1
        if self.player.health >= self.player.max_health * 0.85:
            stars += 1
        return score, min(stars, 3)

    def _win(self):
        if not self.active:
            return
        self.active = False
        self.auto.stop()
        app = kivy.app.App.get_running_app()
        app.audio.stop_music()  # all coins collected, so the level music stops
        app.audio.play_sfx("victory")
        score, stars = self._score_and_stars()
        app.state.record_result(self.index, score, stars)
        next_index = self.index + 1
        if next_index <= levels.NUM_LEVELS:
            app.state.unlock_up_to(next_index)
        buttons = [("Menu", [0.45, 0.45, 0.5, 1], lambda: app.go("levelselect"))]
        if next_index <= levels.NUM_LEVELS:
            buttons.append(("Next", [0.2, 0.7, 0.4, 1], lambda: app.start_level(next_index)))
        stats = self._build_result_stats(score)
        ResultOverlay("Level Clear!", [], buttons, stars=stars, stats=stats).open()

    def _lose(self):
        if not self.active:
            return
        self.active = False
        self.auto.stop()
        app = kivy.app.App.get_running_app()
        app.audio.stop_music()  # level over
        if self.player is not None:
            self.player.dead = True
        app.audio.play_sfx("death")
        buttons = [
            ("Menu", [0.45, 0.45, 0.5, 1], lambda: app.go("levelselect")),
            ("Retry", [0.9, 0.5, 0.2, 1], lambda: app.start_level(self.index)),
        ]
        reason = "Out of time!" if (self.time_left is not None and self.time_left <= 0) else "You were caught!"
        stats = self._build_result_stats(self.score)
        ResultOverlay(reason, [], buttons, stats=stats).open()

    # ----- multiplayer end of game -----
    def _end_coop(self, cleared, reason=""):
        if cleared:
            self._sfx("victory")
            self._mp_finish("Level Clear!", ["You collected every coin together!"])
        else:
            self._mp_finish(reason or "Out of time!",
                            ["Coins left: {}".format(len(self.coins))])

    def _end_versus(self):
        c1, c2 = self.player.collected, self.player2.collected
        if c1 > c2:
            title = "Player 1 Wins!"
        elif c2 > c1:
            title = "Player 2 Wins!"
        else:
            title = "It is a Draw!"
        self._sfx("victory")
        self._mp_finish(title, ["Player 1: {} coins".format(c1),
                                "Player 2: {} coins".format(c2)])

    def _mp_finish(self, title, lines, from_host=True):
        # Show the end-of-game overlay. The host also tells the client to show
        # the same one, so both screens agree on the result.
        if self._ended:
            return
        self._ended = True
        self.active = False
        kivy.app.App.get_running_app().audio.stop_music()
        if self.role == "host" and from_host and self.net is not None:
            self.net.send_event("end", data={"title": title, "lines": lines})
        buttons = [("Menu", [0.45, 0.45, 0.5, 1], self._leave_to_menu)]
        ResultOverlay(title, lines, buttons).open()

    def _leave_to_menu(self):
        app = kivy.app.App.get_running_app()
        if self.net is not None:
            self.net.send_leave()
        app.go("multiplayer")

    def _peer_gone(self):
        # The other player left or the connection dropped.
        if self._ended:
            return
        self._ended = True
        self.active = False
        kivy.app.App.get_running_app().audio.stop_music()
        ui.InfoDialog("Disconnected", "The other player left the game.",
                      on_ok=self._leave_to_menu).open()

    # ----- multiplayer networking -----
    def _pump_net(self, dt):
        # Read messages that the network threads have queued. Runs on the main
        # thread, so it is safe to change widgets here.
        if self.net is None:
            return
        while True:
            try:
                msg = self.net.inbox.get_nowait()
            except queue.Empty:
                break
            kind = msg.get("t")
            if kind == "input" and self.role == "host":
                p2 = self.player2
                if p2 is not None and not p2.dead and p2.down_time <= 0:
                    p2.tx = min(max(float(msg.get("tx", p2.cx)), 0.05), 0.95)
                    p2.ty = min(max(float(msg.get("ty", p2.cy)), 0.05), 0.95)
                    if msg.get("fire"):
                        self.fire(shooter=p2)
            elif kind == "state" and self.role == "client":
                self._apply_snapshot(msg)
            elif kind == "event" and self.role == "client":
                self._handle_event(msg)
            elif kind in ("leave", "_disconnected"):
                self._peer_gone()

    def _handle_event(self, msg):
        kind = msg.get("kind")
        if kind == "sfx":
            kivy.app.App.get_running_app().audio.play_sfx(msg.get("name", ""))
        elif kind == "end":
            data = msg.get("data") or {}
            self._mp_finish(data.get("title", "Game Over"),
                            data.get("lines", []), from_host=False)

    def _broadcast_state(self, dt):
        if self.role != "host" or self.net is None or not self.active:
            return
        self.net.send_state(self._build_snapshot())

    def _build_snapshot(self):
        def pdat(p):
            return [round(p.cx, 4), round(p.cy, 4), round(p.face_x, 3),
                    round(p.face_y, 3), bool(p.moving), bool(p.dead)]
        p1, p2 = self.player, self.player2
        total = self.level["coins"]
        return {
            "t": "state",
            "p1": pdat(p1),
            "p2": pdat(p2),
            "mon": [[round(m.cx, 4), round(m.cy, 4), round(m.face_x, 3),
                     round(m.face_y, 3), int(m.mtype), int(m.hp),
                     bool(m.frozen), bool(m.chasing)] for m in self.monsters],
            "haz": [[round(h.cx, 4), round(h.cy, 4),
                     round(getattr(h, "size_factor", 1.0), 3)] for h in self.hazards],
            "prj": [[round(s.cx, 4), round(s.cy, 4)] for s in self.projectiles],
            "frz": [[round(f.cx, 4), round(f.cy, 4)] for f in self.freezers],
            "coins": [c.index for c in self.coins],
            "hud": {
                "time": None if self.time_left is None else int(self.time_left),
                "freeze": round(self.freeze_time, 2),
                "ammo": p2.ammo,            # the client drives player 2
                "reload": round(p2.reload_time, 2),
                "h1": max(0, int(round(100 * p1.health / p1.max_health))),
                "h2": max(0, int(round(100 * p2.health / p2.max_health))),
                "c1": p1.collected,
                "c2": p2.collected,
                "coins_total": total,
                "coins_left": len(self.coins),
                "mode": self.mode,
            },
        }

    def _apply_snapshot(self, snap):
        if self.player is None:
            return
        self._set_sprite(self.player, snap.get("p1"))
        self._set_sprite(self.player2, snap.get("p2"))
        self._reconcile(self.monsters, snap.get("mon", []),
                        lambda: graphics.MonsterSprite(size_hint=MONSTER_SIZE),
                        self._set_monster)
        self._reconcile(self.hazards, snap.get("haz", []),
                        lambda: graphics.Hazard(size_hint=HAZARD_SIZE),
                        self._set_hazard)
        self._reconcile(self.projectiles, snap.get("prj", []),
                        lambda: graphics.Projectile(size_hint=PROJECTILE_SIZE),
                        self._set_xy)
        self._reconcile(self.freezers, snap.get("frz", []),
                        lambda: graphics.Freezer(size_hint=FREEZER_SIZE),
                        self._set_xy)
        self._apply_coins(snap.get("coins", []))
        self._apply_client_hud(snap.get("hud", {}))

    def _reconcile(self, sprites, rows, make, setter):
        # Make the list of sprites match the rows from the host: add when there
        # are more, remove when there are fewer, then set each one's values.
        while len(sprites) < len(rows):
            s = make()
            self.world.add_widget(s)
            s.start()
            sprites.append(s)
        while len(sprites) > len(rows):
            s = sprites.pop()
            s.stop()
            if s.parent:
                s.parent.remove_widget(s)
        for s, row in zip(sprites, rows):
            setter(s, row)
            place(s)

    def _set_sprite(self, p, row):
        if p is None or not row:
            return
        p.cx, p.cy = row[0], row[1]
        p.face_x, p.face_y = row[2], row[3]
        p.moving = bool(row[4])
        p.dead = bool(row[5])
        place(p)

    def _set_monster(self, m, row):
        m.cx, m.cy = row[0], row[1]
        m.face_x, m.face_y = row[2], row[3]
        m.mtype = row[4]
        m.max_hp = self.level["monster_hp"]
        m.hp = row[5]
        m.frozen = bool(row[6])
        m.chasing = bool(row[7])
        m.moving = True

    def _set_hazard(self, h, row):
        h.cx, h.cy = row[0], row[1]
        h.size_factor = row[2]

    def _set_xy(self, s, row):
        s.cx, s.cy = row[0], row[1]

    def _apply_coins(self, remaining):
        keep = set(remaining)
        for coin in list(self.coins):
            if coin.index not in keep:
                self.coins.remove(coin)
                coin.stop()
                if coin.parent:
                    coin.parent.remove_widget(coin)

    def _apply_client_hud(self, hud):
        if not hud:
            return
        self.time_left = hud.get("time")
        self.freeze_time = hud.get("freeze", 0) or 0
        ammo = hud.get("ammo", 0)
        reload_left = hud.get("reload", 0) or 0
        self.fire_btn.ammo = ammo
        self.fire_btn.ready = True
        self.fire_btn.reloading = reload_left > 0
        if reload_left > 0:
            self.fire_btn.reload_seconds = reload_left
            self.fire_btn.reload_fraction = reload_left / RELOAD_SECONDS
        if self.freeze_time > 0:
            self.freeze_timer.opacity = 1
            self.freeze_timer.seconds = self.freeze_time
            self.freeze_timer.fraction = self.freeze_time / FREEZE_DURATION
        else:
            self.freeze_timer.opacity = 0
        # The client controls player 2, so its health bar follows player 2.
        h2 = hud.get("h2", 100)
        if self.player2 is not None:
            self.player2.max_health = 100
            self.player2.health = h2
        total = hud.get("coins_total", 0)
        left = hud.get("coins_left", 0)
        mode = hud.get("mode")
        if mode == "versus":
            self.coin_label.text = "Coins left {}".format(left)
        else:
            self.coin_label.text = "Coins {}/{}".format(total - left, total)
        self.level_label.text = "Level {}".format(self.level["name"])
        self.time_label.text = "" if self.time_left is None else "Time {}".format(int(self.time_left))
        self._update_health_bar()
        h1 = hud.get("h1", 100)
        if mode == "versus":
            self.mp_label.text = "P1 {}%  coins {}    P2 {}%  coins {}".format(
                h1, hud.get("c1", 0), h2, hud.get("c2", 0))
        else:
            self.mp_label.text = "P1 {}%    P2 {}%".format(h1, h2)

    # ----- pause -----
    def _open_pause(self):
        if not self.active:
            return
        app = kivy.app.App.get_running_app()
        if self.multiplayer:
            # There is no pausing a 2-player game, so this is a leave button.
            self.paused = True
            ui.ConfirmDialog("Leave the game?\nThe other player will be sent back too.",
                             self._leave_to_menu, yes_text="Leave", no_text="Stay",
                             on_no=self._resume).open()
            return
        self.paused = True
        app.audio.stop_music()  # silence while paused

        def quit_to_menu():
            self.active = False
            app.go("levelselect")
        ui.ConfirmDialog("Quit to the level menu?\nThis level's progress is lost.",
                         quit_to_menu, yes_text="Quit", no_text="Resume",
                         on_no=self._resume).open()

    def _resume(self):
        # Resume play and bring the level music back.
        if self.active:
            self.paused = False
            kivy.app.App.get_running_app().audio.play_level_music(self.level["world"])
            if self.auto_mode:
                self.auto.start()

    # ----- auto play -----
    def _toggle_auto(self):
        # Switch between the player and the genetic algorithm.
        self.auto_mode = not self.auto_mode
        self._refresh_auto_button()
        if self.auto_mode:
            if self.active and not self.paused:
                self.auto.start()
        else:
            self.auto.stop()

    def _refresh_auto_button(self):
        if self.auto_mode:
            self.auto_btn.text = "Auto: On"
            self.auto_btn.bg = [0.2, 0.7, 0.4, 1]
            self.auto_indicator.opacity = 1
        else:
            self.auto_btn.text = "Auto: Off"
            self.auto_btn.bg = [0.45, 0.45, 0.5, 1]
            self.auto_indicator.opacity = 0


class CointexApp(kivy.app.App):
    def build(self):
        self.title = "CoinTex"
        # When packaged with PyInstaller the bundled files (logo, music) live in
        # a temp folder pointed to by sys._MEIPASS; otherwise they sit next to
        # this file.
        if getattr(sys, "frozen", False):
            app_dir = sys._MEIPASS
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        # Replace Kivy's default logo with the CoinTex logo in the title bar and
        # taskbar. Skip silently if the file is missing.
        icon_path = os.path.join(app_dir, "cointex_logo.png")
        if os.path.exists(icon_path):
            self.icon = icon_path
            Window.set_icon(icon_path)
        legacy = os.path.join(app_dir, "game_info")
        self.state = GameState(self.user_data_dir, legacy_game_info=legacy)
        self.audio = AudioManager(os.path.join(app_dir, "music"), self.state.get_setting)
        self.current_world = 1
        self.current_level_index = 1

        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))
        self.sm.add_widget(ui.MenuScreen(name="menu"))
        self.sm.add_widget(ui.WorldMapScreen(name="worldmap"))
        self.sm.add_widget(ui.LevelSelectScreen(name="levelselect"))
        self.sm.add_widget(ui.SettingsScreen(name="settings"))
        self.sm.add_widget(ui.AboutScreen(name="about"))
        self.sm.add_widget(ui.TutorialScreen(name="tutorial"))
        self.sm.add_widget(ui.GuideScreen(name="guide"))
        self.sm.add_widget(ui.AutoPlayerScreen(name="autoplayer"))
        self.sm.add_widget(ui.MultiplayerMenuScreen(name="multiplayer"))
        self.sm.add_widget(ui.HostScreen(name="mphost"))
        self.sm.add_widget(ui.JoinScreen(name="mpjoin"))
        self.game = GameScreen(name="game")
        self.sm.add_widget(self.game)
        return self.sm

    def go(self, name):
        self.sm.current = name

    def open_world(self, world):
        self.current_world = world
        self.go("levelselect")

    def start_level(self, index):
        # Show any one-time heads-up messages that are due (a world's new mechanic,
        # or the freeze clock the first time it can appear), then enter the level.
        level = levels.get_level(index)
        world = level["world"]
        first_of_world = (world - 1) * levels.LEVELS_PER_WORLD + 1
        queue = []
        if level["monsters"] > 0 and not self.state.get_setting("gun_hint_seen"):
            self.state.set_setting("gun_hint_seen", True)
            queue.append(GUN_INTRO)
        flag = "intro_seen_w{}".format(world)
        if index == first_of_world and world in WORLD_INTROS and not self.state.get_setting(flag):
            self.state.set_setting(flag, True)
            queue.append(WORLD_INTROS[world])
        if level["monster_hp"] > 1 and not self.state.get_setting("hp_hint_seen"):
            self.state.set_setting("hp_hint_seen", True)
            queue.append(HP_INTRO)
        if level["freezers"] > 0 and not self.state.get_setting("freezer_hint_seen"):
            self.state.set_setting("freezer_hint_seen", True)
            queue.append(FREEZER_INTRO)
        self._show_intros_then_enter(queue, index)

    def _show_intros_then_enter(self, queue, index):
        # Show the queued messages one after another, then start the level.
        if not queue:
            self._enter_level(index)
            return
        title, body = queue[0]
        ui.InfoDialog(title, body,
                      on_ok=lambda: self._show_intros_then_enter(queue[1:], index)).open()

    def _enter_level(self, index):
        self.current_level_index = index
        self.current_world = levels.get_level(index)["world"]
        self.game.load_level(index)
        self.go("game")

    # ----- multiplayer -----
    def start_mp_host(self, mode, seed, conn):
        # Begin a 2-player game as the host. conn is a connected net.NetHost.
        self.game.net = conn
        self.game.load_level(levels.MP_LEVEL, multiplayer=True, role="host",
                             mode=mode, seed=seed)
        self.go("game")

    def start_mp_client(self, mode, seed, conn):
        # Begin a 2-player game as the joining player. conn is a net.NetClient.
        self.game.net = conn
        self.game.load_level(levels.MP_LEVEL, multiplayer=True, role="client",
                             mode=mode, seed=seed)
        self.go("game")


if __name__ == "__main__":
    CointexApp().run()
