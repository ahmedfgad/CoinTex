# Game playing agent for CoinTex using the PyGAD genetic algorithm library.
#
# This does not copy the game. It reuses the main CoinTex engine that lives one
# folder up (main.py, levels.py, graphics.py, audio.py, state.py, ui.py) and adds
# an agent that plays a level on its own.
#
# The sensing and the fitness live in the engine's autoplay.py and are shared with
# the game's built-in Auto play, so this PyGAD version and the in-game version
# behave the same way. The difference is only the search: here PyGAD evolves the
# population, while the built-in version uses a small genetic algorithm in plain
# Python (PyGAD needs numpy, which is awkward to package for phones).
#
# A solution has two genes, a target point [x, y] in the 0..1 play area. The
# fitness puts safety first: keep the path to the target clear of monsters and
# fire and only go for a coin when that is safe. After each generation the best
# target is sent to the player so it walks there, and when a monster is close the
# agent shoots.
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
import autoplay

# Reuse the shared population size so both versions search at the same scale. The
# number of generations is just a high cap; the run stops when the level ends.
POPULATION = autoplay.POPULATION
PARENTS = autoplay.PARENTS
GENERATIONS = 100000


class GameAgent:
    # Drives the player on the current game screen with a PyGAD genetic algorithm.

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
        self._snapshot = autoplay.sense(self.app.game)  # first reading
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

    def _fitness(self, ga_instance, solution, solution_idx):
        return autoplay.fitness(self._snapshot, solution[0], solution[1])

    def _on_generation(self, ga_instance):
        time.sleep(autoplay.RETARGET_DELAY)

        game = self.app.game
        player = None if game is None else game.player
        if self._stop or game is None or player is None or not game.active or not game.coins:
            return "stop"

        best_solution = ga_instance.best_solution()[0]
        player.tx = min(max(float(best_solution[0]), 0.05), 0.95)
        player.ty = min(max(float(best_solution[1]), 0.05), 0.95)

        if autoplay.should_fire(self._snapshot):
            # Firing adds a widget, so it has to run in the main thread.
            Clock.schedule_once(lambda dt: self._fire(), 0)

        self._snapshot = autoplay.sense(game)  # refresh for the next generation

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
