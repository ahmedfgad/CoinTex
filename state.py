# Saves game progress and settings for CoinTex.
# Everything is kept in one JSON file inside the folder the game passes in
# (the Kivy user_data_dir, which can be written to on all platforms).
# Progress from the old version (a pickle file called game_info) is read once
# and copied over.

import json
import os
import pickle

# Settings and their starting values. The "seen" flags remember one-time things:
# the tutorial auto-shows once, and each world's heads-up message shows once.
DEFAULT_SETTINGS = {
    "music_on": True,
    "sfx_on": True,
    "volume": 1.0,   # 0.0 to 1.0
    "ga_style": "balanced",   # auto player: cautious | balanced | aggressive
    "ga_speed": "normal",     # auto player: slow | normal | fast
    "tutorial_seen": False,
    "gun_hint_seen": False,
    "freezer_hint_seen": False,
    "hp_hint_seen": False,
    "intro_seen_w2": False,
    "intro_seen_w3": False,
    "intro_seen_w4": False,
    "intro_seen_w5": False,
    "intro_seen_w6": False,
    "mp_mode": "coop",        # 2-player: coop | versus, chosen by the host
    "mp_last_ip": "",         # the host address the joiner typed last time
}

SAVE_NAME = "cointex_save.json"


class GameState:
    def __init__(self, storage_dir, legacy_game_info=None):
        self.storage_dir = storage_dir
        self.path = os.path.join(storage_dir, SAVE_NAME)
        self.legacy_game_info = legacy_game_info
        self.data = self._load()

    def _default(self):
        return {
            "version": 1,
            "highest_unlocked": 1,   # highest level the player can enter
            "scores": {},            # best score per level, e.g. {"7": 1820}
            "stars": {},             # best stars per level, e.g. {"7": 2}
            "settings": dict(DEFAULT_SETTINGS),
        }

    def _load(self):
        data = self._default()
        if os.path.exists(self.path):
            try:
                with open(self.path) as save_file:
                    loaded = json.load(save_file)
                data.update(loaded)
                # Fill in any setting that an older save did not have.
                settings = dict(DEFAULT_SETTINGS)
                settings.update(data.get("settings", {}))
                data["settings"] = settings
                return data
            except Exception as error:
                print("CoinTex: could not read save, starting fresh.", error)
        # No JSON save yet, so try to bring progress over from the old version.
        self._migrate_legacy(data)
        return data

    def _migrate_legacy(self, data):
        if not self.legacy_game_info or not os.path.exists(self.legacy_game_info):
            return
        try:
            with open(self.legacy_game_info, "rb") as legacy_file:
                info = pickle.load(legacy_file)
            last_level = int(info[0].get("lastlvl", 1))
            data["highest_unlocked"] = max(1, last_level)
            print("CoinTex: brought over old progress up to level", last_level)
        except Exception as error:
            print("CoinTex: could not read old save.", error)

    def save(self):
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w") as save_file:
                json.dump(self.data, save_file)
            os.replace(tmp_path, self.path)
        except Exception as error:
            print("CoinTex: could not save game.", error)

    # progress
    @property
    def highest_unlocked(self):
        return self.data["highest_unlocked"]

    def is_unlocked(self, level_num):
        return level_num <= self.data["highest_unlocked"]

    def unlock_up_to(self, level_num):
        if level_num > self.data["highest_unlocked"]:
            self.data["highest_unlocked"] = level_num
            self.save()

    def record_result(self, level_num, score, stars=0):
        # Store a level result. Returns True if the score is a new best.
        key = str(level_num)
        best = self.data["scores"].get(key, 0)
        improved = score > best
        if improved:
            self.data["scores"][key] = score
        if stars > self.data["stars"].get(key, 0):
            self.data["stars"][key] = stars
        self.save()
        return improved

    def get_score(self, level_num):
        return self.data["scores"].get(str(level_num), 0)

    def get_stars(self, level_num):
        return self.data["stars"].get(str(level_num), 0)

    def total_stars(self):
        return sum(self.data["stars"].values())

    def reset_progress(self):
        # Clear progress and scores but keep the player's settings.
        settings = self.data["settings"]
        self.data = self._default()
        self.data["settings"] = settings
        self.save()

    # settings
    def get_setting(self, key):
        return self.data["settings"].get(key, DEFAULT_SETTINGS.get(key))

    def set_setting(self, key, value):
        self.data["settings"][key] = value
        self.save()
