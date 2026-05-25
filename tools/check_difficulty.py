# Dev check: the difficulty score must never go down as levels go up.
# Run from the project root: python tools/check_difficulty.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels

prev = float("-inf")
dips = []
for g in range(1, levels.NUM_LEVELS + 1):
    score = levels.difficulty_score(levels.get_level(g))
    if score < prev - 1e-9:
        dips.append((g, round(prev, 2), round(score, 2)))
    prev = score

if dips:
    print("NOT monotonic. Dips at (level, prev, this):")
    for d in dips:
        print(" ", d)
    sys.exit(1)

print("OK: difficulty is monotonic across all", levels.NUM_LEVELS, "levels.")
print("score level 1 / 30 / 60:",
      round(levels.difficulty_score(levels.get_level(1)), 1),
      round(levels.difficulty_score(levels.get_level(30)), 1),
      round(levels.difficulty_score(levels.get_level(60)), 1))
