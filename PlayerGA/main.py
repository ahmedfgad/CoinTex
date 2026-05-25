# Game playing agent for CoinTex using a genetic algorithm.
#
# This does not copy the game. It reuses the main CoinTex engine that lives one
# folder up (main.py, levels.py, graphics.py, audio.py, state.py, ui.py) and
# adds an agent that plays a level on its own.
#
# How the agent works:
#   The genes of a solution are a target point [x, y] in the 0..1 play area.
#   The fitness rewards a target that is close to the nearest coin and away from
#   monsters and fire. After each generation the best target is sent to the
#   player so it walks there, and the search runs again from the new position.
#   When a monster gets close the agent shoots it with the limited ammo.
#
# Run it with the project's Python after installing PyGAD:
#   python PlayerGA/main.py

import os
import sys
import time
import threading

# The engine is in the parent folder, so put that folder on the import path.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import pygad

from kivy.clock import Clock

import main as engine
import levels

# How long to wait between two searches. It paces the agent so it picks a new
# target a few times per second instead of as fast as the CPU allows.
RETARGET_DELAY = 0.15
# Shoot when the nearest monster is within this distance of the player.
FIRE_RANGE = 0.22

# Safety is the agent's main concern. It keeps away from monsters and fire and
# only goes for a coin when it can do so without risking its health.
# Coin pull is kept fairly weak so safety wins whenever the two disagree, but
# strong enough that the agent still darts in to grab a coin when a gap opens.
COIN_WEIGHT = 2.0
# Keep at least this much clearance from each monster and fire. A path that stays
# clear is rewarded; one that comes closer is punished, harder the closer it gets.
# The radius sits well above the contact range, so the agent avoids being hit but
# can still slip through a gap to reach a coin.
SAFE_RADIUS = 0.16
SAFE_CLEAR_BONUS = 80.0
SAFE_HIT_PENALTY = 350.0
# When a danger is already this close to the player, also reward moving away from
# it. The path measure cannot tell escape routes apart when the danger sits right
# on the player, so this gives a clear direction to flee.
FLEE_RADIUS = 0.18
FLEE_WEIGHT = 40.0
# Mild preference for shorter moves so the agent grabs near coins first.
NEAR_PLAYER_WEIGHT = 3.0
# Genetic algorithm size. The problem has only two genes, so a small population
# is plenty.
POPULATION = 200
PARENTS = 50
GENERATIONS = 100000


def _point_segment_distance(px, py, ax, ay, bx, by):
    # Shortest distance from the point (px, py) to the line segment that runs
    # from A (ax, ay) to B (bx, by). Used to measure how close a monster or fire
    # is to the path the player would walk to reach a target.
    abx, aby = bx - ax, by - ay
    length_sq = abx * abx + aby * aby
    if length_sq == 0.0:
        t = 0.0
    else:
        t = ((px - ax) * abx + (py - ay) * aby) / length_sq
        t = max(0.0, min(1.0, t))
    closest_x = ax + t * abx
    closest_y = ay + t * aby
    return ((px - closest_x) ** 2 + (py - closest_y) ** 2) ** 0.5


class GameAgent:
    # Drives the player on the current game screen with a genetic algorithm.

    def __init__(self, app):
        self.app = app
        self._thread = None
        self._stop = False
        self._snapshot = None

    def start(self):
        # Stop a previous run first, then play the level that is loaded now.
        self.stop()
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None

    def _run(self):
        self._sense()  # take a first reading before the search starts
        ga = pygad.GA(num_generations=GENERATIONS,
                      num_parents_mating=PARENTS,
                      fitness_func=self._fitness,
                      sol_per_pop=POPULATION,
                      num_genes=2,
                      init_range_low=0.0,
                      init_range_high=1.0,
                      # The coin to reach keeps moving as coins are collected and
                      # the player walks, so this is not a fixed problem. Mutate
                      # each gene with a real chance and drop a mutated gene
                      # anywhere in the play area so the search keeps exploring.
                      mutation_type="random",
                      mutation_probability=0.3,
                      mutation_by_replacement=True,
                      random_mutation_min_val=0.0,
                      random_mutation_max_val=1.0,
                      # Do not carry solutions over with a cached score. The score
                      # of a point changes every step, so every solution must be
                      # measured again each generation or the agent locks onto an
                      # old target.
                      keep_elitism=0,
                      keep_parents=0,
                      on_generation=self._on_generation,
                      suppress_warnings=True)
        ga.run()

    def _sense(self):
        # Read the level into a small snapshot. The search runs in this thread
        # while the game updates in the main thread, so we copy the positions
        # once per generation instead of touching the live widgets many times.
        game = self.app.game
        player = None if game is None else game.player
        if game is None or player is None or not game.active:
            self._snapshot = None
            return

        px, py = player.cx, player.cy
        coins = [(c.cx, c.cy) for c in list(game.coins)]

        # Things to stay away from. Frozen monsters cannot hurt the player, so
        # they are left out while a freeze is active.
        danger = [(h.cx, h.cy) for h in list(game.hazards)]
        if game.freeze_time <= 0:
            danger += [(m.cx, m.cy) for m in list(game.monsters)]

        monsters = [(m.cx, m.cy) for m in list(game.monsters)]
        if monsters:
            nearest_monster = min(((m[0] - px) ** 2 + (m[1] - py) ** 2) ** 0.5 for m in monsters)
        else:
            nearest_monster = None

        # The closest danger to the player. If it is within the flee range the
        # agent should get away from it, even if that means leaving the coins
        # for a moment.
        flee_from = None
        if danger:
            closest = min(danger, key=lambda d: (d[0] - px) ** 2 + (d[1] - py) ** 2)
            if ((closest[0] - px) ** 2 + (closest[1] - py) ** 2) ** 0.5 < FLEE_RADIUS:
                flee_from = closest

        self._snapshot = {
            "coins": coins,
            "danger": danger,
            "player": (px, py),
            "nearest_monster": nearest_monster,
            "flee_from": flee_from,
        }

    def _fitness(self, ga_instance, solution, solution_idx):
        snapshot = self._snapshot
        if snapshot is None or not snapshot["coins"]:
            return 0.0

        target_x, target_y = solution[0], solution[1]
        player_x, player_y = snapshot["player"]

        # Attraction toward the most reachable coin, the one closest to this
        # target. It is weak so safety comes first.
        best_pull = 0.0
        for coin_x, coin_y in snapshot["coins"]:
            distance = ((target_x - coin_x) ** 2 + (target_y - coin_y) ** 2) ** 0.5
            pull = COIN_WEIGHT / (distance + 0.02)
            if pull > best_pull:
                best_pull = pull
        score = best_pull

        # Safety, the main driver. For every monster and fire, look at how close
        # it comes to the straight path the player would walk to reach the target.
        # Reward a path that stays clear and strongly punish one that comes too
        # close, so the agent routes around danger and heads for safe ground
        # instead of walking into it.
        for danger_x, danger_y in snapshot["danger"]:
            gap = _point_segment_distance(danger_x, danger_y,
                                          player_x, player_y, target_x, target_y)
            if gap >= SAFE_RADIUS:
                score += SAFE_CLEAR_BONUS
            else:
                score -= SAFE_HIT_PENALTY * (1.0 - gap / SAFE_RADIUS)

        # If a danger is right next to the player, also reward moving away from
        # it so the agent flees instead of standing still and being hit.
        flee_from = snapshot["flee_from"]
        if flee_from is not None:
            flee_x, flee_y = flee_from
            away = ((target_x - flee_x) ** 2 + (target_y - flee_y) ** 2) ** 0.5
            score += away * FLEE_WEIGHT

        # Mild preference for shorter moves so it grabs near coins first.
        score -= (((target_x - player_x) ** 2 + (target_y - player_y) ** 2) ** 0.5) * NEAR_PLAYER_WEIGHT
        return score

    def _on_generation(self, ga_instance):
        time.sleep(RETARGET_DELAY)

        game = self.app.game
        player = None if game is None else game.player
        if self._stop or game is None or player is None or not game.active or not game.coins:
            return "stop"

        best_solution = ga_instance.best_solution()[0]
        player.tx = min(max(float(best_solution[0]), 0.05), 0.95)
        player.ty = min(max(float(best_solution[1]), 0.05), 0.95)

        snapshot = self._snapshot
        if (snapshot is not None and snapshot["nearest_monster"] is not None
                and snapshot["nearest_monster"] <= FIRE_RANGE):
            # Firing adds a widget, so it has to run in the main thread.
            Clock.schedule_once(lambda dt: self._fire(), 0)

        self._sense()  # refresh for the next generation

    def _fire(self):
        game = self.app.game
        if game is not None and game.active:
            game.fire()  # the engine checks ammo and cooldown and aims for us


class GAApp(engine.CointexApp):
    # The normal game, with the agent attached.

    def build(self):
        screen_manager = super().build()
        # Let the agent open any level for the demo. This stays in memory only,
        # so the real game's saved progress is left untouched.
        self.state.data["highest_unlocked"] = levels.NUM_LEVELS
        self.state.save = lambda *args, **kwargs: None
        self.agent = GameAgent(self)
        return screen_manager

    def start_level(self, index):
        self.agent.stop()
        super().start_level(index)
        self.agent.start()


if __name__ == "__main__":
    GAApp().run()
