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
# How far ahead to project a chasing monster along its heading, and the extra
# clearance to keep from a chaser. These let the agent dodge where a chaser is
# going, not only where it is.
LOOKAHEAD = 0.12
CHASE_MARGIN = 0.05

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

    # Convert a sprite's pixel radius back to the 0..1 space the rest of the math
    # uses, so the agent respects each danger's real (possibly pulsing) size.
    world_w = getattr(getattr(game, "world", None), "width", 0) or 0
    inv_w = (1.0 / world_w) if world_w else 0.0

    def radius_of(sprite):
        return game._radius(sprite) * inv_w if inv_w else 0.05

    # Things to stay away from, each with its current size and (for monsters) its
    # heading and whether it is chasing. Frozen monsters cannot hurt the player,
    # so they are left out while a freeze is active. Fire is never frozen.
    moving_monsters = [] if game.freeze_time > 0 else list(game.monsters)
    dangers = [{"x": h.cx, "y": h.cy, "r": radius_of(h),
                "fx": 0.0, "fy": 0.0, "chasing": False} for h in list(game.hazards)]
    for m in moving_monsters:
        dangers.append({"x": m.cx, "y": m.cy, "r": radius_of(m),
                        "fx": float(m.face_x), "fy": float(m.face_y),
                        "chasing": bool(getattr(m, "chasing", False))})

    # Flat position list kept for the flee logic and as a fallback.
    danger = [(d["x"], d["y"]) for d in dangers]

    all_monsters = list(game.monsters)
    if all_monsters:
        nearest_monster = min(((m.cx - px) ** 2 + (m.cy - py) ** 2) ** 0.5 for m in all_monsters)
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
        "dangers": dangers,
        "player": (px, py),
        "nearest_monster": nearest_monster,
        "flee_from": flee_from,
        "time_left": getattr(game, "time_left", None),
        "time_limit": game.level["time_limit"] if getattr(game, "level", None) else None,
        "coins_left": len(coins),
        "ammo": getattr(game, "ammo", 0),
        "reloading": getattr(game, "reload_time", 0.0) > 0,
    }


def fitness(snapshot, target_x, target_y):
    # Score a candidate target point. Bigger is better.
    if snapshot is None or not snapshot["coins"]:
        return 0.0

    player_x, player_y = snapshot["player"]

    # Urgency rises as the clock runs down: pull harder toward coins and accept a
    # little more risk so the level is finished in time. Safety is never fully
    # abandoned (the penalty reduction is capped).
    urgency = 0.0
    time_left = snapshot.get("time_left")
    time_limit = snapshot.get("time_limit")
    if time_left is not None and time_limit:
        urgency = min(1.0, max(0.0, 1.0 - time_left / (0.6 * time_limit)))
    coin_weight = COIN_WEIGHT * (1.0 + 2.5 * urgency)
    hit_penalty = SAFE_HIT_PENALTY * (1.0 - 0.4 * urgency)

    # When a monster is chasing and the gun is empty, the agent cannot shoot back,
    # so it must commit to escaping: give chasers extra berth and flee harder.
    dangers = snapshot.get("dangers")
    no_ammo = snapshot.get("ammo", 1) <= 0
    chaser_near = no_ammo and any(d.get("chasing") for d in (dangers or []))

    # Attraction toward the most reachable coin, the one closest to this target.
    # It is weak so safety comes first (stronger when the clock is short).
    best_pull = 0.0
    for coin_x, coin_y in snapshot["coins"]:
        distance = ((target_x - coin_x) ** 2 + (target_y - coin_y) ** 2) ** 0.5
        pull = coin_weight / (distance + 0.02)
        if pull > best_pull:
            best_pull = pull
    score = best_pull

    # Safety, the main driver. For every monster and fire, look at how close it
    # comes to the straight path the player would walk to reach the target. The
    # required clearance grows with the danger's own size (so pulsing fires and
    # bigger monsters are respected), and chasers get extra berth plus a look
    # ahead along their heading.
    if dangers is not None:
        for d in dangers:
            lead = LOOKAHEAD if d["chasing"] else 0.0
            ax = d["x"] + d["fx"] * lead
            ay = d["y"] + d["fy"] * lead
            gap = point_segment_distance(ax, ay, player_x, player_y, target_x, target_y)
            extra = 0.0
            if d["chasing"]:
                extra = CHASE_MARGIN + (0.10 if no_ammo else 0.0)
            clear = SAFE_RADIUS + d["r"] + extra
            if gap >= clear:
                score += SAFE_CLEAR_BONUS
            else:
                score -= hit_penalty * (1.0 - gap / clear)
    else:
        for danger_x, danger_y in snapshot["danger"]:
            gap = point_segment_distance(danger_x, danger_y,
                                         player_x, player_y, target_x, target_y)
            if gap >= SAFE_RADIUS:
                score += SAFE_CLEAR_BONUS
            else:
                score -= hit_penalty * (1.0 - gap / SAFE_RADIUS)

    # If a danger is right next to the player, also reward moving away from it so
    # the agent flees instead of standing still and being hit.
    flee_from = snapshot["flee_from"]
    if flee_from is not None:
        flee_x, flee_y = flee_from
        away = ((target_x - flee_x) ** 2 + (target_y - flee_y) ** 2) ** 0.5
        flee_weight = FLEE_WEIGHT * (2.5 if chaser_near else 1.0)
        score += away * flee_weight

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
