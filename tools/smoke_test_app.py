#!/usr/bin/env python3
"""Boot CoinTex and exercise representative UI/game/lifecycle paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
if os.environ.get("XDG_CONFIG_HOME"):
    os.makedirs(os.environ["XDG_CONFIG_HOME"], exist_ok=True)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kivy.clock import Clock
from kivy.config import Config

if os.environ.get("COINTEX_SMOKE_SIZE"):
    width, height = os.environ["COINTEX_SMOKE_SIZE"].lower().split("x", 1)
    Config.set("graphics", "width", width)
    Config.set("graphics", "height", height)
    Config.set("graphics", "resizable", "0")

from kivy.core.window import Window

from main import CointexApp


class SmokeApp(CointexApp):
    def build(self):
        root = super().build()
        # Prevent the first-run tutorial from changing screens underneath the
        # deterministic smoke sequence. This test uses an isolated data folder.
        self.state.data["settings"]["tutorial_seen"] = True
        self.sm.transition.duration = 0
        return root


def main() -> None:
    running = SmokeApp()
    failures = []

    def exercise(_dt):
        try:
            expected = {
                "menu", "worldmap", "levelselect", "settings", "about",
                "privacy", "tutorial", "guide", "autoplayer", "multiplayer",
                "mphost", "mpjoin", "game",
            }
            assert expected == set(running.sm.screen_names)

            # Exercise screens whose entry/exit paths update labels, scroll
            # layouts, audio settings or connection polling without using the
            # internet or opening a host socket.
            for name in ("settings", "about", "privacy", "guide", "autoplayer",
                         "worldmap", "levelselect", "multiplayer", "mpjoin",
                         "multiplayer"):
                running.go(name)

            level_index = int(os.environ.get("COINTEX_SMOKE_LEVEL", "1"))
            running.game.load_level(level_index)
            running.go("game")
            game = running.game
            assert game.active and game.player is not None and game.monsters
            assert not game.fire_btn.disabled

            original_target = (game.player.tx, game.player.ty)
            assert game._on_key(Window, 275, 0, "d", []) is True
            assert game.player.tx > original_target[0]
            game.fire()
            assert game.projectiles

            before = game.time_left
            game.update(10.0)
            assert before - game.time_left <= 0.101

            assert running.on_pause() is True
            assert game.paused and game._background_paused
            running.on_resume()
            assert not game.paused and not game._background_paused

            game._open_pause()
            assert game.paused and game._pause_dialog is not None
            game._pause_dialog.dismiss(animation=False)
            game._resume()
            assert not game.paused

            if os.environ.get("COINTEX_SMOKE_FORCE_CHASER") and game.monsters:
                monster = game.monsters[0]
                monster.cx = min(game.player.cx + 0.05, 0.88)
                monster.cy = min(game.player.cy + 0.02, 0.85)
                game._move_toward(monster, monster.cx, monster.cy, 0)
                monster.chasing = True

            screenshot = os.environ.get("COINTEX_SMOKE_SCREENSHOT")
            if screenshot:
                capture_screen = os.environ.get("COINTEX_SMOKE_SCREEN", "game")
                if capture_screen != "game":
                    running.go(capture_screen)
                else:
                    # Freeze simulation movement while still allowing canvas
                    # animations and hit flashes to settle for a clean capture.
                    game.paused = True
                def capture_and_stop(_capture_dt):
                    actual = Window.screenshot(name=screenshot)
                    destination = Path(screenshot)
                    actual_path = Path(actual)
                    if actual_path != destination:
                        actual_path.replace(destination)
                    print("Smoke screenshot:", destination)
                    print("CoinTex runtime smoke test passed")
                    running.stop()
                # Let the final game screen draw at least one complete frame.
                Clock.schedule_once(capture_and_stop, 1.0)
            else:
                print("CoinTex runtime smoke test passed")
                running.stop()
        except BaseException as error:  # surface scheduled callback errors
            failures.append(error)
            running.stop()

    Clock.schedule_once(exercise, 0.35)
    Clock.schedule_once(lambda _dt: running.stop(), 12.0)
    running.run()
    if failures:
        raise failures[0]


if __name__ == "__main__":
    main()
