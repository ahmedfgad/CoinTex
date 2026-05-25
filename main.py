# CoinTex main file.
#
# The game is a top-down coin collector. You move your character around a level
# to pick up all the coins while dodging monsters and fire, and you can shoot
# the nearest monster. Levels, graphics, audio, saving and the menu screens live
# in separate modules (levels.py, graphics.py, audio.py, state.py, ui.py). This
# file holds the app, the gameplay screen and the rules.

import os
import math
import random

import kivy.app
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import sp, dp

import levels
import graphics
import ui
import autoplay
from state import GameState
from audio import AudioManager

# Tuning values. Positions are kept as a center point in 0..1 over the play area.
PLAYER_SPEED = 0.6          # how fast the player moves, screens per second
PROJECTILE_SPEED = 1.2
FIRE_COOLDOWN = 0.6         # seconds between shots
CONTACT_DAMAGE = 60.0       # health lost per second while touching a monster/fire
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


def place(sprite):
    # Set a sprite's pos_hint from its center (cx, cy) and its size_hint.
    shw, shh = sprite.size_hint
    sprite.pos_hint = {"x": sprite.cx - shw / 2, "y": sprite.cy - shh / 2}


class ResultOverlay(ModalView):
    # Shown when a level is won or lost. Offers next/retry/menu actions.
    def __init__(self, title, lines, buttons, stars=None, **kwargs):
        super().__init__(size_hint=(0.8, 0.6), auto_dismiss=False, **kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(12))
        with box.canvas.before:
            Color(0.12, 0.14, 0.22, 0.98)
            self._bg = RoundedRectangle(radius=[dp(16)])
        box.bind(pos=lambda *a: setattr(self._bg, "pos", box.pos),
                 size=lambda *a: setattr(self._bg, "size", box.size))
        box.add_widget(Label(text=title, font_size=sp(34), bold=True,
                             color=[1, 0.85, 0.2, 1], size_hint_y=0.26))
        if stars is not None:
            box.add_widget(graphics.StarRow(earned=stars, total=3, size_hint_y=0.28))
        box.add_widget(Label(text="\n".join(lines), font_size=sp(20),
                             color=[1, 1, 1, 1], halign="center", size_hint_y=0.22))
        row = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=0.3)
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
        self.ammo = 0
        self.freeze_time = 0.0
        self._update_event = None
        # Auto play: the built-in genetic algorithm can take over from the player.
        self.auto_mode = False
        self.auto = autoplay.AutoPlayer(self)

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
        frac = 0 if self.level is None else max(0.0, self.health / self.max_health)
        self._hp_bar.pos = self.health_holder.pos
        self._hp_bar.size = (self.health_holder.width * frac, self.health_holder.height)
        # green when healthy, red when low
        self._hp_color.rgba = [1 - frac, 0.3 + 0.5 * frac, 0.2, 1]

    # ----- building a level -----
    def load_level(self, index):
        self._clear_sprites()
        self.level = levels.get_level(index)
        self.index = index
        theme = levels.get_world(self.level["world"])
        self.bg.set_theme(theme)
        # In-level music changes per world.
        kivy.app.App.get_running_app().audio.play_level_music(self.level["world"])

        self.max_health = self.level["player_health"]
        self.health = self.max_health
        self.score = 0
        self.kills = 0
        self.collected = 0
        self.cooldown = 0.0
        self.time_left = self.level["time_limit"]
        self.ammo = self.level["ammo"]
        self.freeze_time = 0.0
        self.pending_respawns = []
        self.monster_speed = 0.45 / self.level["monster_speed"]
        self.active = True
        self.paused = False

        # player starts bottom-left
        self.player = graphics.PlayerSprite(size_hint=PLAYER_SIZE)
        self.player.cx, self.player.cy = 0.1, 0.12
        self.player.tx, self.player.ty = self.player.cx, self.player.cy
        place(self.player)
        self.world.add_widget(self.player)
        self.player.start()

        # monsters (they respawn when killed, so they cannot all be cleared)
        for i in range(self.level["monsters"]):
            self._spawn_monster()

        # coins, spread across the width in sections like the original game
        section = 1.0 / self.level["coins"]
        for k in range(self.level["coins"]):
            coin = graphics.Coin(size_hint=COIN_SIZE)
            coin.cx = random.uniform(section * k + 0.03, section * (k + 1) - 0.03)
            coin.cx = min(max(coin.cx, 0.05), 0.95)
            coin.cy = random.uniform(0.2, 0.9)
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
            if random.random() < 0.5:
                # horizontal sweep across x at a fixed random height
                y = random.uniform(0.18, 0.85)
                hazard.ax, hazard.ay = 0.08, y
                hazard.bx, hazard.by = 0.92, y
            else:
                # vertical sweep up and down at a fixed random column
                x = random.uniform(0.08, 0.92)
                hazard.ax, hazard.ay = x, 0.12
                hazard.bx, hazard.by = x, 0.9
            hazard.t = random.uniform(0, 1)
            hazard.period = self.level["fire_speed"]
            hazard.cx, hazard.cy = hazard.ax, hazard.ay
            place(hazard)
            self.world.add_widget(hazard)
            hazard.start()
            self.hazards.append(hazard)

        # rare freeze pickups
        for i in range(self.level["freezers"]):
            freezer = graphics.Freezer(size_hint=FREEZER_SIZE)
            freezer.cx, freezer.cy = random.uniform(0.15, 0.9), random.uniform(0.2, 0.85)
            place(freezer)
            self.world.add_widget(freezer)
            freezer.start()
            self.freezers.append(freezer)

        self.fire_btn.ammo = self.ammo
        self.fire_btn.ready = True
        self.freeze_timer.opacity = 0
        self._refresh_hud()

        # Keep the chosen play mode (manual or auto) when moving between levels.
        self._refresh_auto_button()
        if self.auto_mode:
            self.auto.start()
        else:
            self.auto.stop()

    def _random_point(self):
        return random.uniform(0.1, 0.95), random.uniform(0.15, 0.95)

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
        place(monster)
        self.world.add_widget(monster)
        monster.start()
        self.monsters.append(monster)

    def _clear_sprites(self):
        for sprite in ([self.player] + self.monsters + self.coins + self.hazards
                       + self.projectiles + self.freezers):
            if sprite is not None:
                sprite.stop()
                if sprite.parent:
                    sprite.parent.remove_widget(sprite)
        for entry in self.pending_respawns:
            marker = entry["marker"]
            if marker.parent:
                marker.parent.remove_widget(marker)
        self.player = None
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
        Window.bind(on_key_down=self._on_key)

    def on_leave(self):
        self.auto.stop()
        if self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        Window.unbind(on_key_down=self._on_key)
        kivy.app.App.get_running_app().audio.stop_music()
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
        if self.active and not self.paused and self.player is not None:
            self.player.tx = min(max(touch.sx, 0.05), 0.95)
            self.player.ty = min(max(touch.sy, 0.05), 0.95)
            return True
        return False

    # ----- main loop -----
    def update(self, dt):
        if not self.active or self.paused or self.player is None:
            return
        if self.cooldown > 0:
            self.cooldown -= dt

        frozen = self.freeze_time > 0
        if frozen:
            self.freeze_time -= dt
            if self.freeze_time <= 0:
                self.freeze_time = 0.0
                for monster in self.monsters:
                    monster.frozen = False
                frozen = False

        self._move_toward(self.player, self.player.tx, self.player.ty, PLAYER_SPEED * dt)

        if not frozen:
            for monster in self.monsters:
                reached = self._move_toward(monster, monster.tx, monster.ty, monster.speed * dt)
                if reached:
                    monster.tx, monster.ty = self._random_point()

        for hazard in self.hazards:
            hazard.t = (hazard.t + dt / hazard.period) % 1.0
            phase = 0.5 - 0.5 * math.cos(hazard.t * 2 * math.pi)
            hazard.cx = hazard.ax + (hazard.bx - hazard.ax) * phase
            hazard.cy = hazard.ay + (hazard.by - hazard.ay) * phase
            place(hazard)

        self._update_projectiles(dt)
        self._process_respawns(dt)
        self._check_coins()
        self._check_freezers()
        self._check_damage(dt)
        self._update_timer(dt)
        self._update_health_bar()
        self._update_combat_hud()

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
            if self._overlap(self.player, freezer, factor=0.8):
                self.freezers.remove(freezer)
                freezer.stop()
                if freezer.parent:
                    freezer.parent.remove_widget(freezer)
                self.freeze_time = FREEZE_DURATION
                for monster in self.monsters:
                    monster.frozen = True
                kivy.app.App.get_running_app().audio.play_sfx("coin")

    def _update_combat_hud(self):
        self.fire_btn.ammo = self.ammo
        self.fire_btn.ready = self.cooldown <= 0
        if self.freeze_time > 0:
            self.freeze_timer.opacity = 1
            self.freeze_timer.seconds = self.freeze_time
            self.freeze_timer.fraction = self.freeze_time / FREEZE_DURATION
        else:
            self.freeze_timer.opacity = 0

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
        return min(sprite.size_hint[0] * self.world.width,
                   sprite.size_hint[1] * self.world.height) / 2

    def _overlap(self, a, b, factor=0.8):
        ax, ay = self._px(a)
        bx, by = self._px(b)
        reach = (self._radius(a) + self._radius(b)) * factor
        return (ax - bx) ** 2 + (ay - by) ** 2 <= reach * reach

    # ----- combat -----
    def fire(self):
        if not self.active or self.paused or self.player is None:
            return
        if self.cooldown > 0 or self.ammo <= 0 or not self.monsters:
            return
        target = self._nearest_monster()
        if target is None:
            return
        self.cooldown = FIRE_COOLDOWN
        self.ammo -= 1
        self.fire_btn.ammo = self.ammo
        shot = graphics.Projectile(size_hint=PROJECTILE_SIZE)
        shot.cx, shot.cy = self.player.cx, self.player.cy
        shot.target = target
        place(shot)
        self.world.add_widget(shot)
        shot.start()
        self.projectiles.append(shot)
        kivy.app.App.get_running_app().audio.play_sfx("shoot")

    def _nearest_monster(self):
        best = None
        best_d = 999
        for monster in self.monsters:
            d = (monster.cx - self.player.cx) ** 2 + (monster.cy - self.player.cy) ** 2
            if d < best_d:
                best_d = d
                best = monster
        return best

    def _update_projectiles(self, dt):
        for shot in list(self.projectiles):
            target = shot.target if shot.target in self.monsters else self._nearest_monster()
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
        app = kivy.app.App.get_running_app()
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
            # drop a countdown marker where it died; it returns there at zero
            marker = graphics.RespawnMarker(size_hint=RESPAWN_MARKER_SIZE)
            marker.cx, marker.cy = monster.cx, monster.cy
            place(marker)
            self.world.add_widget(marker)
            self.pending_respawns.append({"t": RESPAWN_DELAY, "x": monster.cx,
                                          "y": monster.cy, "marker": marker})
            app.audio.play_sfx("monster_death")
        else:
            app.audio.play_sfx("hit")
        self._refresh_hud()

    def _burst(self, sprite, color):
        cx, cy = self._px(sprite)
        self.world.add_widget(graphics.ParticleBurst((cx, cy), color=color))

    # ----- coins, damage, timer -----
    def _check_coins(self):
        app = kivy.app.App.get_running_app()
        for coin in list(self.coins):
            if self._overlap(self.player, coin, factor=0.7):
                self.coins.remove(coin)
                coin.stop()
                if coin.parent:
                    coin.parent.remove_widget(coin)
                self.collected += 1
                self.score += COIN_POINTS
                app.audio.play_sfx("coin")
                self._refresh_hud()
        if not self.coins and self.active:
            self._win()

    def _check_damage(self, dt):
        if self.player.dead:
            return
        touching = False
        if self.freeze_time <= 0:  # frozen monsters do not hurt the player
            for monster in self.monsters:
                if self._overlap(self.player, monster, factor=0.7):
                    touching = True
                    break
        if not touching:
            for hazard in self.hazards:
                if self._overlap(self.player, hazard, factor=0.6):
                    touching = True
                    break
        if touching:
            self.health -= CONTACT_DAMAGE * dt
            self.player.hit_flash()
            if self.health <= 0:
                self.health = 0
                self._lose()

    def _update_timer(self, dt):
        if self.time_left is None:
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            self._lose()
        self._refresh_hud()

    def _refresh_hud(self):
        total = self.level["coins"]
        self.coin_label.text = "Coins {}/{}".format(self.collected, total)
        self.level_label.text = "Level {}".format(self.level["name"])
        if self.time_left is None:
            self.time_label.text = ""
        else:
            self.time_label.text = "Time {}".format(int(self.time_left))

    # ----- win / lose -----
    def _score_and_stars(self):
        score = self.score + int(self.health) * 3
        if self.time_left is not None:
            score += int(self.time_left) * TIME_BONUS
        # stars: finishing = 1, plus health and (when timed) time bonuses
        stars = 1
        if self.health >= self.max_health * 0.5:
            stars += 1
        if self.health >= self.max_health * 0.85:
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
        lines = ["Score: {}".format(score)]
        ResultOverlay("Level Clear!", lines, buttons, stars=stars).open()

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
        ResultOverlay(reason, ["Score: {}".format(self.score)], buttons).open()

    # ----- pause -----
    def _open_pause(self):
        if not self.active:
            return
        self.paused = True
        app = kivy.app.App.get_running_app()
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
        app_dir = os.path.dirname(os.path.abspath(__file__))
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
        self.game = GameScreen(name="game")
        self.sm.add_widget(self.game)
        return self.sm

    def go(self, name):
        self.sm.current = name

    def open_world(self, world):
        self.current_world = world
        self.go("levelselect")

    def start_level(self, index):
        self.current_level_index = index
        self.current_world = levels.get_level(index)["world"]
        self.game.load_level(index)
        self.go("game")


if __name__ == "__main__":
    CointexApp().run()
