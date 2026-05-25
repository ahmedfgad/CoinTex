# Level data for CoinTex.
#
# There are 6 worlds with 10 levels each, so 60 levels in total. Every level is
# built from a single global level number g (1..60) by the build_levels function
# below. World number = (g-1)//10 + 1.
#
# Difficulty curve
# ----------------
# Levels get harder with DEPTH, not with more things on screen. The enemy counts
# are kept low and nearly flat so the game stays smooth on every device; the
# challenge comes from how the few enemies behave. All the knobs change in one
# direction as g goes up, so a level is never easier than the one before it:
#   coins           : 5  ->  30   (the only count that still grows; the goal size)
#   monster count   : 1  ->   2   (capped low on purpose)
#   monster hp      : 1  ->   3
#   fire count      : 1  ->   2   (capped low on purpose)
#   monster speed   : slow -> fast (move duration 2.0s -> ~0.8s, lower is faster)
#   fire speed      : slow -> fast (sweep duration 6.0s -> 2.0s)
#   enemy speed mult: world 2+, 1.0 -> 1.4 (capped so chasers stay escapable)
#   fire pulse      : world 3+, fires grow and shrink so the danger zone breathes
#   chase range/time: world 4+, the nearest monster locks on and chases the player
#   gun reload      : world 4+, the gun refills itself after the ammo runs out
#   contact damage  : world 5+, 50 -> 70 dps (the late game is less forgiving)
#   player health   : 60 -> 30
#   time limit      : every level is timed; generous early, tight late
# Each world introduces one new mechanic, shown to the player with a one-time
# heads-up message before that world (see WORLD_INTROS in main.py).
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

        # Entity counts: capped LOW and nearly flat. Keeping the number of sprites
        # small at every level is what keeps the game smooth. Coins are the one
        # count that still grows, since they are the goal.
        coins = _clamp(5 + (g - 1) // 2, 5, 30)
        monster_count = _clamp(1 + (g - 1) // 12, 1, 2)
        monster_hp = _clamp(1 + (g - 1) // 20, 1, 3)
        fire_count = _clamp(1 + (g - 1) // 16, 1, 2)

        # Behavior knobs that scale with depth without adding any sprites. Each new
        # mechanic is gated to start at a world boundary, so it can be introduced
        # with a heads-up message and the early worlds stay gentle:
        #   world 2: faster enemies   world 3: pulsing fire
        #   world 4: chasing monsters world 5: harder hits
        monster_speed = round(_clamp(2.0 - (g - 1) * 0.02, 0.8, 2.0), 2)
        fire_speed = round(_clamp(6.0 - (g - 1) * 0.07, 2.0, 6.0), 2)
        enemy_speed_mult = round(_clamp(1.0 + max(0, g - 10) * 0.009, 1.0, 1.4), 3)
        chase_range = round(_clamp(max(0, g - 30) * 0.008, 0.0, 0.22), 3)
        chase_time = round(_clamp(max(0, g - 30) * 0.035, 0.0, 1.0), 2)
        pulse_amp = round(_clamp(max(0, g - 20) * 0.012, 0.0, 0.45), 3)
        pulse_period = round(_clamp(2.0 - (g - 1) * 0.02, 1.0, 2.0), 2)
        # Contact damage stays at the base through world 4, then rises in worlds 5-6
        # so the late game is less forgiving. Pressure mainly comes from the
        # reactable mechanics (chase, fire pulse, time), not from one touch killing.
        contact_damage = round(_clamp(50.0 + max(0, g - 40) * 1.0, 50.0, 70.0), 1)

        # Every level is timed. The limit only ever shrinks with depth (it is a
        # function of g alone), so the time pressure never eases on a later level.
        time_limit = int(_clamp(150 - (g - 1) * 1.6, 60, 150))

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
            "enemy_speed_mult": enemy_speed_mult,
            "chase_range": chase_range,
            "chase_time": chase_time,
            "pulse_amp": pulse_amp,
            "pulse_period": pulse_period,
            "contact_damage": contact_damage,
            # From world 4 on, the gun reloads itself after the ammo runs out.
            "gun_reload": world >= 4,
            "time_limit": time_limit,
            # Health shrinks from 60 down to 30 across the game, so touching a
            # monster or fire matters much more in later levels.
            "player_health": _clamp(60 - (g - 1) // 2, 30, 60),
            # Ammo is 1 to 3 and equals a monster's hit points, so a full clip can
            # take down exactly one monster (which then respawns). Firing is for
            # clearing a blocker, not for winning.
            "ammo": _clamp(monster_hp, 1, 3),
            # A freeze pickup pauses the monsters for a while. It is a rare
            # reward: only about every 7th level has one.
            "freezers": 1 if g % 7 == 0 else 0,
        })
    return levels


LEVELS = build_levels()


def get_level(index):
    # index is 1-based (1..NUM_LEVELS).
    return LEVELS[index - 1]


# The level id used for 2-player games. It is a string so it can never be
# mistaken for a campaign level number (1..60).
MP_LEVEL = "mp"


def get_mp_level(seed=None):
    # A single arena used for 2-player games. It is not part of the 1..60
    # campaign and never changes a player's progress. Entity counts are kept
    # modest so the action stays smooth over a network, and there is no chasing
    # or pulsing fire in this first version so both screens stay predictable.
    # The seed makes both devices lay the arena out the same way.
    return {
        "index": MP_LEVEL,
        "world": 6,
        "world_index": 0,
        "name": "Arena",
        "coins": 22,
        "monsters": 2,
        "monster_hp": 1,
        "monster_speed": 1.2,
        "fires": 2,
        "fire_speed": 3.5,
        "enemy_speed_mult": 1.0,
        "chase_range": 0.0,
        "chase_time": 0.0,
        "pulse_amp": 0.0,
        "pulse_period": 2.0,
        "contact_damage": 50.0,
        "gun_reload": True,
        "time_limit": 120,
        "player_health": 80,
        "ammo": 1,
        "freezers": 0,
        "seed": seed,
    }


def levels_in_world(world):
    return [lvl for lvl in LEVELS if lvl["world"] == world]


def get_world(world):
    return WORLDS[world - 1]


def difficulty_score(level):
    # A rough single number for how hard a level is. Used to check the curve
    # only increases. Bigger means harder. Every term is monotonic in g, so the
    # total is monotonic by construction (verified by tools/check_difficulty.py).
    time_pressure = (160 - level["time_limit"]) * 0.3
    return (
        level["coins"] * 0.5
        + level["monsters"] * level["monster_hp"] * 3.0
        + (2.2 - level["monster_speed"]) * 8.0
        + (level["enemy_speed_mult"] - 1.0) * 25.0
        + level["fires"] * 2.0
        + (6.5 - level["fire_speed"]) * 2.0
        + level["chase_range"] * 60.0
        + level["chase_time"] * 8.0
        + level["pulse_amp"] * 20.0
        + (60 - level["player_health"]) * 0.3
        + (level["contact_damage"] - 45.0) * 0.2
        + time_pressure
    )
