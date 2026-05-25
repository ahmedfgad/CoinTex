# Built-in auto play for CoinTex.
#
# This lets the game play itself with a small genetic algorithm. It is written in
# plain Python with no extra libraries (no numpy, no pygad), so it ships inside
# the Android and iOS apps without any change to the build. The standalone
# research version in PlayerGA/ uses the PyGAD library instead, but both share the
# same sensing and fitness in this file so they behave the same way.
#
# How it plays:
#   A solution is a target point [x, y] in the 0..1 play area. The fitness puts
#   safety first: it keeps the path to the target clear of monsters and fire and
#   only lets the player go for a coin when that can be done without much risk.
#   A few times per second the best target is sent to the player so it walks
#   there, and when a monster is close the player shoots.

import random
import threading
import time

from kivy.clock import Clock

# Re-target a few times per second.
RETARGET_DELAY = 0.15
# Shoot when the nearest monster is within this distance of the player.
FIRE_RANGE = 0.22

# Safety is the main concern. The player keeps away from monsters and fire and
# only goes for a coin when it can do so without risking its health. Coin pull is
# weak so safety wins when the two disagree, but strong enough that the player
# still darts in to grab a coin when a gap opens.
COIN_WEIGHT = 2.0
SAFE_RADIUS = 0.16
SAFE_CLEAR_BONUS = 80.0
SAFE_HIT_PENALTY = 350.0
FLEE_RADIUS = 0.18
FLEE_WEIGHT = 40.0
NEAR_PLAYER_WEIGHT = 3.0

# Size of the genetic algorithm. The problem has only two values to find, so a
# small population is plenty and stays fast even on a phone.
POPULATION = 200
PARENTS = 50
KEEP_BEST = 4
MUTATION_PROB = 0.3


def point_segment_distance(px, py, ax, ay, bx, by):
    # Shortest distance from the point (px, py) to the line segment from A to B.
    # Used to measure how close a monster or fire is to the path the player would
    # walk to reach a target.
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


def sense(game):
    # Copy what the agent needs from the level into a small snapshot. The search
    # runs in its own thread while the game updates in the main thread, so the
    # positions are copied once per step instead of read from the live widgets
    # many times. Returns None when there is nothing to play.
    player = None if game is None else game.player
    if game is None or player is None or not game.active:
        return None

    px, py = player.cx, player.cy
    coins = [(c.cx, c.cy) for c in list(game.coins)]

    # Things to stay away from. Frozen monsters cannot hurt the player, so they
    # are left out while a freeze is active. Fire is never frozen.
    danger = [(h.cx, h.cy) for h in list(game.hazards)]
    if game.freeze_time <= 0:
        danger += [(m.cx, m.cy) for m in list(game.monsters)]

    monsters = [(m.cx, m.cy) for m in list(game.monsters)]
    if monsters:
        nearest_monster = min(((m[0] - px) ** 2 + (m[1] - py) ** 2) ** 0.5 for m in monsters)
    else:
        nearest_monster = None

    # The closest danger to the player. If it is within the flee range the agent
    # should get away from it, even if that means leaving the coins for a moment.
    flee_from = None
    if danger:
        closest = min(danger, key=lambda d: (d[0] - px) ** 2 + (d[1] - py) ** 2)
        if ((closest[0] - px) ** 2 + (closest[1] - py) ** 2) ** 0.5 < FLEE_RADIUS:
            flee_from = closest

    return {
        "coins": coins,
        "danger": danger,
        "player": (px, py),
        "nearest_monster": nearest_monster,
        "flee_from": flee_from,
    }


def fitness(snapshot, target_x, target_y):
    # Score a candidate target point. Bigger is better.
    if snapshot is None or not snapshot["coins"]:
        return 0.0

    player_x, player_y = snapshot["player"]

    # Attraction toward the most reachable coin, the one closest to this target.
    # It is weak so safety comes first.
    best_pull = 0.0
    for coin_x, coin_y in snapshot["coins"]:
        distance = ((target_x - coin_x) ** 2 + (target_y - coin_y) ** 2) ** 0.5
        pull = COIN_WEIGHT / (distance + 0.02)
        if pull > best_pull:
            best_pull = pull
    score = best_pull

    # Safety, the main driver. For every monster and fire, look at how close it
    # comes to the straight path the player would walk to reach the target. Reward
    # a path that stays clear and strongly punish one that comes too close, so the
    # agent routes around danger and heads for safe ground instead of through it.
    for danger_x, danger_y in snapshot["danger"]:
        gap = point_segment_distance(danger_x, danger_y,
                                     player_x, player_y, target_x, target_y)
        if gap >= SAFE_RADIUS:
            score += SAFE_CLEAR_BONUS
        else:
            score -= SAFE_HIT_PENALTY * (1.0 - gap / SAFE_RADIUS)

    # If a danger is right next to the player, also reward moving away from it so
    # the agent flees instead of standing still and being hit.
    flee_from = snapshot["flee_from"]
    if flee_from is not None:
        flee_x, flee_y = flee_from
        away = ((target_x - flee_x) ** 2 + (target_y - flee_y) ** 2) ** 0.5
        score += away * FLEE_WEIGHT

    # Mild preference for shorter moves so it grabs near coins first.
    score -= (((target_x - player_x) ** 2 + (target_y - player_y) ** 2) ** 0.5) * NEAR_PLAYER_WEIGHT
    return score


def should_fire(snapshot):
    # Decide whether to shoot this step. The game still checks ammo and cooldown
    # and aims at the nearest monster on its own, so this only says when to try.
    return (snapshot is not None
            and snapshot["nearest_monster"] is not None
            and snapshot["nearest_monster"] <= FIRE_RANGE)


class AutoPlayer:
    # Plays the given game screen with a small genetic algorithm running in its
    # own thread. Call start to take over and stop to hand control back.

    def __init__(self, screen):
        self.screen = screen
        self._thread = None
        self._stop = False

    def start(self):
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
        # Start from a population of random target points spread over the screen.
        population = [(random.random(), random.random()) for _ in range(POPULATION)]

        while not self._stop:
            screen = self.screen
            snapshot = sense(screen)
            if snapshot is None or not snapshot["coins"]:
                break

            # While the game is paused, wait without moving or shooting.
            if screen.paused:
                time.sleep(RETARGET_DELAY)
                continue

            # Score everyone against the current snapshot. The level keeps
            # changing, so every target is scored fresh each step.
            ranked = sorted(population,
                            key=lambda point: fitness(snapshot, point[0], point[1]),
                            reverse=True)

            best = ranked[0]
            player = screen.player
            if player is None or not screen.active:
                break
            player.tx = min(max(best[0], 0.05), 0.95)
            player.ty = min(max(best[1], 0.05), 0.95)

            if should_fire(snapshot):
                # Firing adds a widget, so it has to run in the main thread.
                Clock.schedule_once(lambda dt: self._fire(), 0)

            population = self._next_generation(ranked)
            time.sleep(RETARGET_DELAY)

    def _next_generation(self, ranked):
        # Keep the best few, then fill the rest with children of the top parents.
        parents = ranked[:PARENTS]
        new_population = list(ranked[:KEEP_BEST])
        while len(new_population) < POPULATION:
            mother = random.choice(parents)
            father = random.choice(parents)
            child_x = mother[0] if random.random() < 0.5 else father[0]
            child_y = mother[1] if random.random() < 0.5 else father[1]
            if random.random() < MUTATION_PROB:
                child_x = random.random()
            if random.random() < MUTATION_PROB:
                child_y = random.random()
            new_population.append((child_x, child_y))
        return new_population

    def _fire(self):
        screen = self.screen
        if screen.active and not screen.paused:
            screen.fire()  # the game checks ammo and cooldown and aims for us
