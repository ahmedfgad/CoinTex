import json
import tempfile
import unittest
from pathlib import Path

import levels
from state import GameState


class GameStateTests(unittest.TestCase):
    def test_malformed_values_are_normalized_without_losing_valid_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cointex_save.json"
            path.write_text(json.dumps({
                "highest_unlocked": 999,
                "scores": {"1": 250, "2": -1, "bad": "value"},
                "stars": {"1": 9, "2": -4},
                "settings": {
                    "music_on": False,
                    "volume": 5,
                    "ga_style": "unknown",
                    "mp_mode": "versus",
                    "mp_last_ip": " 192.168.1.5 ",
                },
            }), encoding="utf-8")

            state = GameState(directory)
            self.assertEqual(state.highest_unlocked, levels.NUM_LEVELS)
            self.assertEqual(state.get_score(1), 250)
            self.assertEqual(state.get_score(2), 0)
            self.assertEqual(state.get_stars(1), 3)
            self.assertEqual(state.get_stars(2), 0)
            self.assertFalse(state.get_setting("music_on"))
            self.assertEqual(state.get_setting("volume"), 1.0)
            self.assertEqual(state.get_setting("ga_style"), "balanced")
            self.assertEqual(state.get_setting("mp_mode"), "versus")
            self.assertEqual(state.get_setting("mp_last_ip"), "192.168.1.5")

    def test_truncated_json_starts_with_safe_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "cointex_save.json").write_text("{", encoding="utf-8")
            state = GameState(directory)
            self.assertEqual(state.highest_unlocked, 1)
            self.assertEqual(state.total_stars(), 0)

    def test_result_values_are_clamped_and_saved_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            state = GameState(directory)
            state.record_result(1, -20, 99)
            self.assertEqual(state.get_score(1), 0)
            self.assertEqual(state.get_stars(1), 3)
            self.assertTrue((Path(directory) / "cointex_save.json").is_file())
            self.assertFalse((Path(directory) / "cointex_save.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
