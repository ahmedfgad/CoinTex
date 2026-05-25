# Dev check: enemy counts stay low and flat, and every level is timed.
# This is what keeps the game light. Run: python tools/check_entity_counts.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels

MAX_MONSTERS = 2
MAX_FIRES = 2

bad = []
for g in range(1, levels.NUM_LEVELS + 1):
    lvl = levels.get_level(g)
    if lvl["monsters"] > MAX_MONSTERS:
        bad.append((g, "monsters", lvl["monsters"]))
    if lvl["fires"] > MAX_FIRES:
        bad.append((g, "fires", lvl["fires"]))
    if lvl["time_limit"] is None:
        bad.append((g, "time_limit", None))

print("level : monsters fires coins  time")
for g in (1, 10, 20, 30, 40, 50, 60):
    lvl = levels.get_level(g)
    print(" {:>4} :    {}      {}    {:>3}    {}s".format(
        g, lvl["monsters"], lvl["fires"], lvl["coins"], lvl["time_limit"]))

if bad:
    print("FAIL:", bad)
    sys.exit(1)
print("OK: monsters<=%d, fires<=%d, every level timed." % (MAX_MONSTERS, MAX_FIRES))
