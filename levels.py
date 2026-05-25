# Level data for CoinTex.
#
# There are 6 worlds with 10 levels each, so 60 levels in total. Every level is
# built from a single global level number g (1..60) by the build_levels function
# below. World number = (g-1)//10 + 1.
#
# Difficulty curve
# ----------------
# All the knobs below change in one direction as g goes up, so a level is never
# easier than the one before it:
#   coins          : 5  ->  30   (more coins to collect, longer time on screen)
#   monster count  : 1  ->   7
#   monster hp     : 1  ->   3   (worlds 1-2 = 1 hit, 3-4 = 2 hits, 5-6 = 3 hits)
#   monster speed  : slow -> fast (move duration 2.0s -> ~0.8s, lower is faster)
#   fire count     : 0  ->  10
#   fire speed     : slow -> fast (sweep duration 6.0s -> 2.0s)
#   time limit     : none for worlds 1-2, then a shrinking limit
#   player health  : stays at 100; the pressure comes from the knobs above
# To retune, edit the formulas in build_levels. To make a single level easier or
# harder, edit its dict in the LEVELS list after it is built.

LEVELS_PER_WORLD = 10
NUM_WORLDS = 6
NUM_LEVELS = LEVELS_PER_WORLD * NUM_WORLDS

# Theme for each world. Colors are (r, g, b) from 0 to 1 and are used by the
# graphics code for backgrounds and accents.
WORLDS = [
    {"name": "Meadow",  "top": (0.55, 0.80, 0.45), "bottom": (0.20, 0.55, 0.30), "accent": (1.00, 0.85, 0.20)},
    {"name": "Desert",  "top": (0.98, 0.85, 0.55), "bottom": (0.85, 0.55, 0.25), "accent": (0.95, 0.45, 0.20)},
    {"name": "Ocean",   "top": (0.45, 0.75, 0.95), "bottom": (0.10, 0.35, 0.65), "accent": (0.95, 0.95, 0.40)},
    {"name": "Cavern",  "top": (0.45, 0.35, 0.60), "bottom": (0.15, 0.10, 0.25), "accent": (0.70, 0.95, 0.55)},
    {"name": "Volcano", "top": (0.85, 0.35, 0.20), "bottom": (0.30, 0.08, 0.08), "accent": (1.00, 0.75, 0.20)},
    {"name": "Space",   "top": (0.20, 0.20, 0.40), "bottom": (0.03, 0.03, 0.10), "accent": (0.60, 0.90, 1.00)},
]


def _clamp(value, low, high):
    return max(low, min(high, value))


def build_levels():
    levels = []
    for g in range(1, NUM_LEVELS + 1):
        world = (g - 1) // LEVELS_PER_WORLD + 1
        world_index = (g - 1) % LEVELS_PER_WORLD + 1

        coins = _clamp(5 + (g - 1) // 2, 5, 30)
        monster_count = _clamp(1 + (g - 1) // 9, 1, 7)
        monster_hp = _clamp(1 + (g - 1) // 20, 1, 3)
        monster_speed = round(_clamp(2.0 - (g - 1) * 0.02, 0.8, 2.0), 2)
        fire_count = _clamp((g - 1) // 5, 0, 10)
        fire_speed = round(_clamp(6.0 - (g - 1) * 0.07, 2.0, 6.0), 2)

        if g <= 20:
            time_limit = None
        else:
            time_limit = _clamp(150 - (g - 20) * 2, 50, 150)

        levels.append({
            "index": g,
            "world": world,
            "world_index": world_index,
            "name": "{}-{}".format(world, world_index),
            "coins": coins,
            "monsters": monster_count,
            "monster_hp": monster_hp,
            "monster_speed": monster_speed,
            "fires": fire_count,
            "fire_speed": fire_speed,
            "time_limit": time_limit,
            "player_health": 100,
        })
    return levels


LEVELS = build_levels()


def get_level(index):
    # index is 1-based (1..NUM_LEVELS).
    return LEVELS[index - 1]


def levels_in_world(world):
    return [lvl for lvl in LEVELS if lvl["world"] == world]


def get_world(world):
    return WORLDS[world - 1]


def difficulty_score(level):
    # A rough single number for how hard a level is. Used to check the curve
    # only increases. Bigger means harder.
    time_pressure = 0 if level["time_limit"] is None else (160 - level["time_limit"]) * 0.3
    return (
        level["coins"] * 0.5
        + level["monsters"] * level["monster_hp"] * 3.0
        + (2.2 - level["monster_speed"]) * 8.0
        + level["fires"] * 2.0
        + (6.5 - level["fire_speed"]) * 2.0
        + time_pressure
    )
